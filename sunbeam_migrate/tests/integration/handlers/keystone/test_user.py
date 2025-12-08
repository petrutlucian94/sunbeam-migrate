# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.keystone import (
    utils as keystone_test_utils,
)


def test_migrate_user(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    # Create a domain first
    domain = keystone_test_utils.create_test_domain(test_source_session)
    request.addfinalizer(
        lambda: keystone_test_utils.delete_domain(test_source_session, domain.id)
    )

    # Create a user with the domain
    user = keystone_test_utils.create_test_user(
        test_source_session, domain_id=domain.id, email="test@example.com"
    )
    request.addfinalizer(
        lambda: keystone_test_utils.delete_user(test_source_session, user.id)
    )

    test_utils.call_migrate(
        test_config_path,
        [
            "start",
            "--resource-type=user",
            "--include-dependencies",
            user.id,
        ],
    )

    dest_domain_id = test_utils.get_destination_resource_id(
        test_config_path, "domain", domain.id
    )
    dest_user = test_destination_session.identity.find_user(
        user.name, domain_id=dest_domain_id
    )
    assert dest_user, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: keystone_test_utils.delete_user(test_destination_session, dest_user.id)
    )

    keystone_test_utils.check_migrated_user(
        test_source_session, test_destination_session, user, dest_user
    )
