# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.neutron import utils as neutron_utils


def _check_migrated_security_group(source_sg, destination_sg):
    fields = [
        "description",
        "name",
        "stateful",
    ]
    for field in fields:
        source_attr = getattr(source_sg, field)
        dest_attr = getattr(destination_sg, field)
        assert source_attr == dest_attr, f"{field} attribute mismatch"


def _check_migrated_security_group_rule(source_rule, dest_rule):
    fields = [
        "description",
        "direction",
        "ether_type",
        "port_range_min",
        "port_range_max",
        "protocol",
        "remote_ip_prefix",
    ]
    for field in fields:
        source_attr = getattr(source_rule, field)
        dest_attr = getattr(dest_rule, field)
        assert source_attr == dest_attr, f"{field} attribute mismatch"


def test_migrate_security_group(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    sg = neutron_utils.create_test_security_group(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_security_group(sg.id)
    )

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=security-group",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_sg = test_destination_session.network.find_security_group(sg.name)
    assert dest_sg, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_security_group(dest_sg.id)
    )

    _check_migrated_security_group(sg, dest_sg)

    test_utils.call_migrate(
        test_config_path,
        ["cleanup-source", "--resource-type=security-group", "--source-id", sg.id],
    )

    assert not test_source_session.network.find_security_group(sg.id), (
        "cleanup-source didn't remove the resource"
    )


def test_migrate_security_group_and_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    sg = neutron_utils.create_test_security_group(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_security_group(sg.id)
    )

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=security-group",
            "--cleanup-source",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_sg = test_destination_session.network.find_security_group(sg.name)
    assert dest_sg, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_security_group(dest_sg.id)
    )

    _check_migrated_security_group(sg, dest_sg)

    assert not test_source_session.network.find_security_group(sg.id), (
        "cleanup-source didn't remove the resource"
    )


def test_migrate_security_group_with_members(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    sg = neutron_utils.create_test_security_group(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_security_group(sg.id)
    )

    rule = neutron_utils.create_test_security_group_rule(test_source_session, sg)
    request.addfinalizer(
        lambda: test_source_session.network.delete_security_group_rule(rule.id)
    )

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=security-group",
            "--include-members",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_sg = test_destination_session.network.find_security_group(sg.name)
    assert dest_sg, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_security_group(dest_sg.id)
    )

    _check_migrated_security_group(sg, dest_sg)

    dest_rule = None
    for candidate in test_destination_session.network.security_group_rules(
        security_group_id=dest_sg.id
    ):
        if (
            candidate.direction == "ingress"
            and candidate.ether_type == "IPv4"
            and candidate.protocol == "tcp"
            and candidate.port_range_min == 8080
            and candidate.port_range_max == 8080
        ):
            dest_rule = candidate
            break
    assert dest_rule, "security group member rule was not migrated"


def test_migrate_security_group_rule_and_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    sg = neutron_utils.create_test_security_group(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_security_group(sg.id)
    )

    rule = neutron_utils.create_test_security_group_rule(test_source_session, sg)
    request.addfinalizer(
        lambda: test_source_session.network.delete_security_group_rule(rule.id)
    )

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=security-group-rule",
            "--include-dependencies",
            "--cleanup-source",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_sg = test_destination_session.network.find_security_group(sg.name)
    assert dest_sg, "couldn't find migrated security group"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_security_group(dest_sg.id)
    )

    dest_rule = None
    for candidate in test_destination_session.network.security_group_rules(
        security_group_id=dest_sg.id
    ):
        if (
            candidate.direction == rule.direction
            and candidate.ether_type == rule.ether_type
            and candidate.protocol == rule.protocol
            and candidate.port_range_min == rule.port_range_min
            and candidate.port_range_max == rule.port_range_max
        ):
            dest_rule = candidate
            break
    assert dest_rule, "couldn't find migrated rule"

    _check_migrated_security_group_rule(rule, dest_rule)

    assert not test_source_session.network.find_security_group_rule(rule.id), (
        "cleanup-source didn't remove the security group rule"
    )
