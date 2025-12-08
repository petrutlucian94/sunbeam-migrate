# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.keystone import (
    utils as keystone_test_utils,
)


def test_migrate_role_with_cleanup(
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

    # Create a role with the domain
    role = keystone_test_utils.create_test_role(
        test_source_session, domain_id=domain.id
    )
    request.addfinalizer(
        lambda: keystone_test_utils.delete_role(test_source_session, role.id)
    )

    test_utils.call_migrate(
        test_config_path,
        [
            "start",
            "--resource-type=role",
            "--include-dependencies",
            role.id,
        ],
    )

    dest_domain_id = test_utils.get_destination_resource_id(
        test_config_path, "domain", domain.id
    )
    dest_role = test_destination_session.identity.find_role(
        role.name, domain_id=dest_domain_id
    )
    assert dest_role, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: keystone_test_utils.delete_role(test_destination_session, dest_role.id)
    )

    keystone_test_utils.check_migrated_role(
        test_source_session, test_destination_session, role, dest_role
    )
