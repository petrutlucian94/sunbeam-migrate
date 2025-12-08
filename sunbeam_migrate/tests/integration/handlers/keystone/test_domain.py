# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import pytest
from openstack import exceptions as openstack_exc

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.keystone import (
    utils as keystone_test_utils,
)


def test_migrate_domain_with_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    domain = keystone_test_utils.create_test_domain(test_source_session)
    request.addfinalizer(
        lambda: keystone_test_utils.delete_domain(test_source_session, domain.id)
    )

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=domain", "--cleanup-source", domain.id],
    )

    dest_domain = test_destination_session.identity.find_domain(domain.name)
    assert dest_domain, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: keystone_test_utils.delete_domain(
            test_destination_session, dest_domain.id
        )
    )

    keystone_test_utils.check_migrated_domain(domain, dest_domain)

    with pytest.raises(openstack_exc.ResourceNotFound):
        test_source_session.identity.get_domain(domain.id)


def test_migrate_domain_with_members(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    # Create a domain
    domain = keystone_test_utils.create_test_domain(test_source_session)
    request.addfinalizer(
        lambda: keystone_test_utils.delete_domain(test_source_session, domain.id)
    )

    # Create a project in the domain
    project = keystone_test_utils.create_test_project(
        test_source_session, domain_id=domain.id
    )
    request.addfinalizer(
        lambda: keystone_test_utils.delete_project(test_source_session, project.id)
    )

    # Create a user assigned to the project
    user = keystone_test_utils.create_test_user(
        test_source_session,
        domain_id=domain.id,
        default_project_id=project.id,
        email="test@example.com",
    )
    request.addfinalizer(
        lambda: keystone_test_utils.delete_user(test_source_session, user.id)
    )

    # Create roles
    role1 = keystone_test_utils.create_test_role(
        test_source_session, domain_id=domain.id
    )
    request.addfinalizer(
        lambda: keystone_test_utils.delete_role(test_source_session, role1.id)
    )

    role2 = keystone_test_utils.create_test_role(
        test_source_session, domain_id=domain.id
    )
    request.addfinalizer(
        lambda: keystone_test_utils.delete_role(test_source_session, role2.id)
    )

    # Create user role assignments
    # Project-level assignment
    test_source_session.identity.assign_project_role_to_user(project, user, role1)

    # Domain-level assignment
    test_source_session.identity.assign_domain_role_to_user(domain, user, role2)

    # Migrate domain with --include-members
    test_utils.call_migrate(
        test_config_path,
        [
            "start",
            "--resource-type=domain",
            "--include-members",
            "--include-dependencies",
            domain.id,
        ],
    )

    # Verify domain was migrated
    dest_domain = test_destination_session.identity.find_domain(domain.name)
    assert dest_domain, "couldn't find migrated domain"
    request.addfinalizer(
        lambda: keystone_test_utils.delete_domain(
            test_destination_session, dest_domain.id
        )
    )
    keystone_test_utils.check_migrated_domain(domain, dest_domain)

    # Verify project was migrated
    dest_project_id = test_utils.get_destination_resource_id(
        test_config_path, "project", project.id
    )
    dest_project = test_destination_session.identity.get_project(dest_project_id)
    assert dest_project, "couldn't find migrated project"
    request.addfinalizer(
        lambda: keystone_test_utils.delete_project(
            test_destination_session, dest_project.id
        )
    )
    keystone_test_utils.check_migrated_project(
        test_source_session, test_destination_session, project, dest_project
    )

    # Verify user was migrated
    dest_user_id = test_utils.get_destination_resource_id(
        test_config_path, "user", user.id
    )
    dest_user = test_destination_session.identity.get_user(dest_user_id)
    assert dest_user, "couldn't find migrated user"
    request.addfinalizer(
        lambda: keystone_test_utils.delete_user(test_destination_session, dest_user.id)
    )
    keystone_test_utils.check_migrated_user(
        test_source_session, test_destination_session, user, dest_user
    )

    # Verify roles were migrated
    dest_role1_id = test_utils.get_destination_resource_id(
        test_config_path, "role", role1.id
    )
    dest_role1 = test_destination_session.identity.get_role(dest_role1_id)
    assert dest_role1, "couldn't find migrated role1"
    request.addfinalizer(
        lambda: keystone_test_utils.delete_role(test_destination_session, dest_role1.id)
    )
    keystone_test_utils.check_migrated_role(
        test_source_session, test_destination_session, role1, dest_role1
    )

    dest_role2_id = test_utils.get_destination_resource_id(
        test_config_path, "role", role2.id
    )
    dest_role2 = test_destination_session.identity.get_role(dest_role2_id)
    assert dest_role2, "couldn't find migrated role2"
    request.addfinalizer(
        lambda: keystone_test_utils.delete_role(test_destination_session, dest_role2.id)
    )
    keystone_test_utils.check_migrated_role(
        test_source_session, test_destination_session, role2, dest_role2
    )

    # Verify role assignments were recreated
    # Check project-level assignment
    project_assignments = list(
        test_destination_session.identity.role_assignments(
            user_id=dest_user.id, project_id=dest_project.id
        )
    )
    role_ids = [a.role["id"] for a in project_assignments if a.role.get("id")]
    assert dest_role1_id in role_ids, "Project-level role assignment not found"

    # Check domain-level assignment
    domain_assignments = list(
        test_destination_session.identity.role_assignments(
            user_id=dest_user.id, domain_id=dest_domain.id
        )
    )
    role_ids = [a.role["id"] for a in domain_assignments if a.role.get("id")]
    assert dest_role2_id in role_ids, "Domain-level role assignment not found"
