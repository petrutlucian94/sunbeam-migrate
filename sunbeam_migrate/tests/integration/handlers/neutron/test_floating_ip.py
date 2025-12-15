# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.neutron import utils as neutron_utils


def _create_floating_ip(session, network, subnet):
    floating_ip = session.network.create_ip(
        floating_network_id=network.id,
        subnet_id=subnet.id,
        description="sunbeam-migrate floating ip test",
    )
    return session.network.get_ip(floating_ip.id)


def _check_migrated_floating_ip(
    source_floating_ip, dest_floating_ip, dest_network_id, dest_subnet_id
):
    fields = [
        "description",
        "floating_ip_address",
    ]
    for field in fields:
        assert getattr(source_floating_ip, field) == getattr(dest_floating_ip, field), (
            f"{field} attribute mismatch"
        )

    assert dest_floating_ip.floating_network_id == dest_network_id, (
        "floating network was not mapped to destination"
    )
    source_subnet_id = getattr(source_floating_ip, "subnet_id", None)
    if source_subnet_id:
        assert dest_subnet_id, "destination subnet id missing"
        dest_subnet_id_present = getattr(dest_floating_ip, "subnet_id", None)
        if dest_subnet_id_present:
            assert dest_subnet_id_present == dest_subnet_id, (
                "floating IP subnet was not mapped to destination"
            )


def test_migrate_floating_ip_with_dependencies_and_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    external_network = neutron_utils.create_test_network(
        test_source_session, is_router_external=True
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_network(external_network.id)
    )

    external_subnet = neutron_utils.create_test_subnet(
        test_source_session, external_network
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_subnet(external_subnet.id)
    )

    floating_ip = _create_floating_ip(
        test_source_session, external_network, external_subnet
    )
    request.addfinalizer(lambda: test_source_session.network.delete_ip(floating_ip.id))

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=floating-ip",
            "--include-dependencies",
            "--cleanup-source",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_network_id = test_utils.get_destination_resource_id(
        test_config_path, "network", external_network.id
    )
    dest_network = test_destination_session.network.get_network(dest_network_id)
    assert dest_network, "couldn't find migrated external network"

    dest_subnet_id = test_utils.get_destination_resource_id(
        test_config_path, "subnet", external_subnet.id
    )
    dest_subnet = test_destination_session.network.get_subnet(dest_subnet_id)
    assert dest_subnet, "couldn't find migrated external subnet"

    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(dest_network_id)
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(dest_subnet_id)
    )
    dest_floating_ip = test_destination_session.network.find_ip(
        floating_ip.floating_ip_address
    )
    assert dest_floating_ip, "couldn't find migrated floating IP"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_ip(dest_floating_ip.id)
    )

    _check_migrated_floating_ip(
        floating_ip, dest_floating_ip, dest_network_id, dest_subnet_id
    )

    assert not test_source_session.network.find_ip(floating_ip.id), (
        "cleanup-source didn't remove the floating IP"
    )


def test_migrate_floating_ip_batch_with_filter(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    floating_ips = []
    networks = []
    subnets = []

    for _ in range(2):
        network = neutron_utils.create_test_network(
            test_source_session, is_router_external=True
        )
        networks.append(network)
        request.addfinalizer(
            lambda net_id=network.id: test_source_session.network.delete_network(net_id)
        )

        subnet = neutron_utils.create_test_subnet(test_source_session, network)
        subnets.append(subnet)
        request.addfinalizer(
            lambda subnet_id=subnet.id: test_source_session.network.delete_subnet(
                subnet_id
            )
        )

        fip = _create_floating_ip(test_source_session, network, subnet)
        floating_ips.append(fip)
        request.addfinalizer(
            lambda fip_id=fip.id: test_source_session.network.delete_ip(fip_id)
        )

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=floating-ip",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
            "--include-dependencies",
            "--cleanup-source",
        ],
    )

    for floating_ip, network, subnet in zip(floating_ips, networks, subnets):
        dest_network_id = test_utils.get_destination_resource_id(
            test_config_path, "network", network.id
        )
        dest_subnet_id = test_utils.get_destination_resource_id(
            test_config_path, "subnet", subnet.id
        )

        request.addfinalizer(
            lambda net_id=dest_network_id: (
                test_destination_session.network.delete_network(net_id)
            )
        )
        request.addfinalizer(
            lambda subnet_id=dest_subnet_id: (
                test_destination_session.network.delete_subnet(subnet_id)
            )
        )
        dest_floating_ip = test_destination_session.network.find_ip(
            floating_ip.floating_ip_address
        )
        assert dest_floating_ip, "couldn't find migrated floating IP"
        request.addfinalizer(
            lambda fip_id=dest_floating_ip.id: (
                test_destination_session.network.delete_ip(fip_id)
            )
        )

        _check_migrated_floating_ip(
            floating_ip, dest_floating_ip, dest_network_id, dest_subnet_id
        )

        assert not test_source_session.network.find_ip(floating_ip.id), (
            "cleanup-source didn't remove the floating IP"
        )
