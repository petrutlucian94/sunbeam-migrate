# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.neutron import utils as neutron_utils


def _check_migrated_network(test_config, source_network, destination_network):
    fields = [
        "availability_zone_hints",
        "description",
        "dns_domain",
        "is_admin_state_up",
        "is_default",
        "is_port_security_enabled",
        "is_router_external",
        "is_shared",
        "mtu",
        "name",
        "provider_network_type",
        "provider_physical_network",
        "segments",
    ]
    if test_config.preserve_network_segmentation_id:
        fields.append("provider_segmentation_id")

    for field in fields:
        source_attr = getattr(source_network, field)
        dest_attr = getattr(destination_network, field)
        assert source_attr == dest_attr, f"{field} attribute mismatch"


def _check_migrated_subnet(source_subnet, destination_subnet):
    fields = [
        "allocation_pools",
        "cidr",
        "description",
        "dns_nameservers",
        "dns_publish_fixed_ip",
        "is_dhcp_enabled",
        "gateway_ip",
        "host_routes",
        "ip_version",
        "ipv6_address_mode",
        "ipv6_ra_mode",
        "name",
        "prefix_length",
        "segment_id",
        "service_types",
        "subnet_pool_id",
        "use_default_subnet_pool",
    ]
    for field in fields:
        source_attr = getattr(source_subnet, field, None)
        dest_attr = getattr(destination_subnet, field, None)
        assert source_attr == dest_attr, f"{field} attribute mismatch"


def test_migrate_network_and_cleanup(
    request,
    test_config,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    network = neutron_utils.create_test_network(test_source_session)
    request.addfinalizer(lambda: test_source_session.network.delete_network(network.id))

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=network",
            "--include-dependencies",
            "--cleanup-source",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_network = test_destination_session.network.find_network(network.name)
    assert dest_network, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(dest_network.id)
    )

    _check_migrated_network(test_config, network, dest_network)

    assert not test_source_session.network.find_network(network.id), (
        "cleanup-source didn't remove the resource"
    )


def test_migrate_network_with_members(
    request,
    test_config,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    network = neutron_utils.create_test_network(test_source_session)
    request.addfinalizer(lambda: test_source_session.network.delete_network(network.id))

    subnet = neutron_utils.create_test_subnet(test_source_session, network)
    request.addfinalizer(lambda: test_source_session.network.delete_subnet(subnet.id))

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=network",
            "--include-dependencies",
            "--include-members",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_network = test_destination_session.network.find_network(network.name)
    assert dest_network, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(dest_network.id)
    )

    _check_migrated_network(test_config, network, dest_network)

    dest_subnets = list(
        test_destination_session.network.subnets(network_id=dest_network.id)
    )
    assert dest_subnets, "no subnets migrated as members of the network"


def test_migrate_subnet_and_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    network = neutron_utils.create_test_network(test_source_session)
    request.addfinalizer(lambda: test_source_session.network.delete_network(network.id))

    subnet = neutron_utils.create_test_subnet(test_source_session, network)
    request.addfinalizer(lambda: test_source_session.network.delete_subnet(subnet.id))

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=subnet",
            "--include-dependencies",
            "--cleanup-source",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_net = test_destination_session.network.find_network(network.name)
    assert dest_net, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(dest_net.id)
    )

    dest_subnet = test_destination_session.network.find_subnet(subnet.name)
    assert dest_subnet, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(dest_subnet.id)
    )

    _check_migrated_subnet(subnet, dest_subnet)

    assert not test_source_session.network.find_subnet(subnet.id), (
        "cleanup-source didn't remove the resource"
    )
