# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils


def _create_test_network(session, is_router_external=False):
    network = session.network.create_network(
        name=test_utils.get_test_resource_name(),
        is_router_external=is_router_external,
    )
    # Refresh network information.
    return session.network.get_network(network.id)


def _create_test_subnet(session, network, cidr="192.168.10.0/24"):
    subnet = session.network.create_subnet(
        network_id=network.id,
        ip_version=4,
        cidr=cidr,
        name=test_utils.get_test_resource_name(),
    )
    # Refresh subnet information.
    return session.network.get_subnet(subnet.id)


def _create_test_router(session, external_network=None, external_subnet=None):
    kwargs = {
        "name": test_utils.get_test_resource_name(),
        "is_admin_state_up": True,
    }

    if external_network:
        external_gateway_info = {"network_id": external_network.id}
        if external_subnet:
            external_gateway_info["external_fixed_ips"] = [
                {"subnet_id": external_subnet.id}
            ]
        kwargs["external_gateway_info"] = external_gateway_info

    router = session.network.create_router(**kwargs)
    # Refresh router information.
    return session.network.get_router(router.id)


def _check_migrated_router(source_router, destination_router):
    fields = [
        "availability_zone_hints",
        "description",
        "flavor_id",
        "is_admin_state_up",
        "is_distributed",
        "is_ha",
        "name",
    ]
    for field in fields:
        source_attr = getattr(source_router, field, None)
        dest_attr = getattr(destination_router, field, None)
        assert source_attr == dest_attr, f"{field} attribute mismatch"


def test_migrate_router_and_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    router = _create_test_router(test_source_session)
    request.addfinalizer(lambda: test_source_session.network.delete_router(router.id))

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=router", "--cleanup-source", router.id],
    )

    dest_router = test_destination_session.network.find_router(router.name)
    assert dest_router, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_router(dest_router.id)
    )

    _check_migrated_router(router, dest_router)

    assert not test_source_session.network.find_router(router.id), (
        "cleanup-source didn't remove the resource"
    )


def test_migrate_router_with_dependencies_and_members(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    # Create external network and subnet for gateway
    external_network = _create_test_network(
        test_source_session, is_router_external=True
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_network(external_network.id)
    )

    external_subnet = _create_test_subnet(
        test_source_session, external_network, cidr="10.0.0.0/24"
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_subnet(external_subnet.id)
    )

    # Create internal network and subnet
    internal_network = _create_test_network(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_network(internal_network.id)
    )

    internal_subnet = _create_test_subnet(
        test_source_session, internal_network, cidr="192.168.20.0/24"
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_subnet(internal_subnet.id)
    )

    # Create router with external gateway
    router = _create_test_router(test_source_session, external_network, external_subnet)
    request.addfinalizer(lambda: test_source_session.network.delete_router(router.id))

    # Attach internal subnet to router
    test_source_session.network.add_interface_to_router(
        router.id, subnet_id=internal_subnet.id
    )
    request.addfinalizer(
        lambda: test_source_session.network.remove_interface_from_router(
            router.id, subnet_id=internal_subnet.id
        )
    )

    # Migrate router with both dependencies and members
    test_utils.call_migrate(
        test_config_path,
        [
            "start",
            "--resource-type=router",
            "--include-dependencies",
            "--include-members",
            router.id,
        ],
    )

    # Verify migrated router
    dest_router = test_destination_session.network.find_router(router.name)
    assert dest_router, "couldn't find migrated router"

    _check_migrated_router(router, dest_router)

    # Verify external gateway is set up correctly
    dest_external_gateway_info = getattr(dest_router, "external_gateway_info", None)
    assert dest_external_gateway_info, "external gateway info not migrated"

    dest_external_network_id = dest_external_gateway_info.get("network_id")
    assert dest_external_network_id, "external network id not set"

    dest_external_network = test_destination_session.network.get_network(
        dest_external_network_id
    )

    # Verify external subnet was migrated as dependency
    dest_external_fixed_ips = dest_external_gateway_info.get("external_fixed_ips", [])
    assert dest_external_fixed_ips, "external fixed IPs not migrated"

    dest_external_subnet_id = dest_external_fixed_ips[0].get("subnet_id")
    assert dest_external_subnet_id, "external subnet id not set"

    dest_external_subnet = test_destination_session.network.get_subnet(
        dest_external_subnet_id
    )

    # Verify internal subnet was migrated as member
    dest_internal_subnet_id = test_utils.get_destination_resource_id(
        test_config_path, "subnet", internal_subnet.id
    )
    dest_internal_subnet = test_destination_session.network.get_subnet(
        dest_internal_subnet_id
    )
    assert dest_internal_subnet, "internal subnet not migrated as member"

    # Verify the internal subnet is attached to the router
    dest_ports = list(
        test_destination_session.network.ports(
            device_id=dest_router.id, device_owner="network:router_interface"
        )
    )
    assert dest_ports, "no ports attached to migrated router"

    # Check if the subnet is attached through any port
    attached_subnet_ids = set()
    for port in dest_ports:
        for fixed_ip in getattr(port, "fixed_ips", []):
            subnet_id = fixed_ip.get("subnet_id")
            if subnet_id:
                attached_subnet_ids.add(subnet_id)

    assert dest_internal_subnet_id in attached_subnet_ids, (
        "internal subnet not attached to router"
    )

    # Cleanup: delete the migrated internal network and subnet
    dest_internal_network_id = test_utils.get_destination_resource_id(
        test_config_path, "network", internal_network.id
    )

    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(
            dest_internal_network_id
        )
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(
            dest_external_network.id
        )
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(dest_internal_subnet_id)
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(dest_external_subnet.id)
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_router(dest_router.id)
    )
    request.addfinalizer(
        lambda: test_destination_session.network.remove_gateway_from_router(
            dest_router.id
        )
    )
    request.addfinalizer(
        lambda: test_destination_session.network.remove_interface_from_router(
            dest_router.id, subnet_id=dest_internal_subnet_id
        )
    )
