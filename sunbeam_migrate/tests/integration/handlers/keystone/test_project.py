# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.keystone import (
    utils as keystone_test_utils,
)


def test_migrate_project_with_cleanup(
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

    # Create a project with the domain
    project = keystone_test_utils.create_test_project(
        test_source_session, domain_id=domain.id
    )
    request.addfinalizer(
        lambda: keystone_test_utils.delete_project(test_source_session, project.id)
    )

    test_utils.call_migrate(
        test_config_path,
        [
            "start",
            "--resource-type=project",
            "--include-dependencies",
            project.id,
        ],
    )

    dest_project = test_destination_session.identity.find_project(project.name)
    assert dest_project, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: keystone_test_utils.delete_project(
            test_destination_session, dest_project.id
        )
    )

    keystone_test_utils.check_migrated_project(
        test_source_session, test_destination_session, project, dest_project
    )
