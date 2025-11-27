# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.barbican import (
    utils as barbican_test_utils,
)
from sunbeam_migrate.utils import barbican_utils


def test_migrate_secret_container_batch(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_source_project,
):
    container_count = 3
    source_secrets = []
    source_containers = []
    for idx in range(container_count):
        secret_1 = barbican_test_utils.create_test_secret(request, test_source_session)
        secret_2 = barbican_test_utils.create_test_secret(request, test_source_session)
        container = barbican_test_utils.create_test_secret_container(
            request, test_source_session, [secret_1, secret_2]
        )

        source_secrets += [secret_1, secret_2]
        source_containers.append(container)

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=secret-container",
            "--filter",
            f"owner-id:{test_source_project.id}",
            "--cleanup-source",
            "--include-dependencies",
        ],
    )

    for source_container in source_containers:
        dest_container = test_destination_session.key_manager.find_container(
            source_container.name
        )
        assert dest_container, "couldn't find migrated resource"
        request.addfinalizer(
            lambda: test_destination_session.key_manager.delete_container(
                dest_container.container_id
            )
        )

        barbican_test_utils.check_migrated_secret_container(
            test_source_session,
            test_destination_session,
            source_container,
            dest_container,
        )

        assert not test_source_session.key_manager.find_container(
            source_container.name
        ), "cleanup-source didn't remove the resource"

    for source_secret in source_secrets:
        dest_secret_id = test_utils.get_destination_resource_id(
            test_config_path,
            "secret",
            source_secret.secret_ref,
        )
        assert dest_secret_id, "Missing migrated resource id"
        dest_secret = test_destination_session.key_manager.get_secret(
            barbican_utils.parse_barbican_url(dest_secret_id)
        )
        assert dest_secret, "couldn't find migrated resource"
        request.addfinalizer(
            lambda: test_destination_session.key_manager.delete_secret(
                dest_secret.secret_id
            )
        )

        barbican_test_utils.check_migrated_secret(source_secret, dest_secret)

        # The openstacksdk "find_secret" method is broken.
        # It returns unpopulated objects even if the service returns 404.
        # Also, name lookups do not work.
        # "get_secret" doesn't properly handle 404 errors either.
        source_secret_names = [
            secret.name for secret in test_source_session.key_manager.secrets()
        ]
        assert source_secret.name not in source_secret_names, (
            "cleanup-source didn't remove the resource"
        )
