# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from openstack import exceptions as openstack_exc

from sunbeam_migrate.tests.integration import utils as test_utils


def _create_test_network(session):
    network = session.network.create_network(name=test_utils.get_test_resource_name())
    return session.network.get_network(network.id)


def _create_test_subnet(session, network, cidr="192.168.10.0/24"):
    subnet = session.network.create_subnet(
        network_id=network.id,
        ip_version=4,
        cidr=cidr,
        name=test_utils.get_test_resource_name(),
    )
    return session.network.get_subnet(subnet.id)


def _create_test_security_group(session):
    sg = session.network.create_security_group(
        name=test_utils.get_test_resource_name(),
        description="test security group",
    )
    return session.network.get_security_group(sg.id)


def _create_test_port(session, network, subnet=None, security_group=None, fixed_ip=None):
    port_kwargs = {
        "network_id": network.id,
        "name": test_utils.get_test_resource_name(),
    }

    if subnet:
        fixed_ips = [{"subnet_id": subnet.id}]
        if fixed_ip:
            fixed_ips[0]["ip_address"] = fixed_ip
        port_kwargs["fixed_ips"] = fixed_ips

    if security_group:
        port_kwargs["security_group_ids"] = [security_group.id]

    port = session.network.create_port(**port_kwargs)
    return session.network.get_port(port.id)


def _check_migrated_port(source_port, destination_port):
    """Check that the migrated port matches the source port."""
    fields = [
        "admin_state_up",
        "description",
        "name",
        "port_security_enabled",
    ]
    for field in fields:
        source_val = getattr(source_port, field, None)
        dest_val = getattr(destination_port, field, None)
        assert source_val == dest_val, f"{field} mismatch: {source_val} != {dest_val}"

    # Check security groups
    source_sg_ids = sorted(source_port.security_group_ids or [])
    dest_sg_ids = sorted(destination_port.security_group_ids or [])
    assert len(source_sg_ids) == len(dest_sg_ids), (
        f"security group count mismatch: {len(source_sg_ids)} != {len(dest_sg_ids)}"
    )

    # Check fixed IPs - we check that the structure is preserved
    # (actual IP addresses and subnet IDs are mapped during migration)
    source_fixed_ips = source_port.fixed_ips or []
    dest_fixed_ips = destination_port.fixed_ips or []
    assert len(source_fixed_ips) == len(dest_fixed_ips), (
        f"fixed IP count mismatch: {len(source_fixed_ips)} != {len(dest_fixed_ips)}"
    )

    # Check that fixed IPs have IP addresses if they had them before
    for source_fip, dest_fip in zip(source_fixed_ips, dest_fixed_ips):
        if "ip_address" in source_fip:
            assert "ip_address" in dest_fip, "fixed IP missing ip_address"
            assert dest_fip["ip_address"] == source_fip["ip_address"], (
                f"fixed IP address mismatch: {dest_fip['ip_address']} != {source_fip['ip_address']}"
            )
        if "subnet_id" in source_fip:
            assert "subnet_id" in dest_fip, "fixed IP missing subnet_id"


def _delete_port(session, port_id: str):
    session.network.delete_port(port_id, ignore_missing=True)


def test_migrate_port_with_dependencies(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    """Test port migration with all associated resources and fixed IP."""
    # Create network, subnet, and security group on source
    network = _create_test_network(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_network(network.id)
    )

    subnet = _create_test_subnet(test_source_session, network, cidr="10.0.0.0/24")
    request.addfinalizer(
        lambda: test_source_session.network.delete_subnet(subnet.id)
    )

    security_group = _create_test_security_group(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_security_group(security_group.id)
    )

    # Create port with subnet, security group, and fixed IP
    port = _create_test_port(
        test_source_session,
        network,
        subnet=subnet,
        security_group=security_group,
        fixed_ip="10.0.0.10",
    )
    request.addfinalizer(lambda: _delete_port(test_source_session, port.id))

    # Migrate port with dependencies
    test_utils.call_migrate(
        test_config_path,
        [
            "start",
            "--resource-type=port",
            "--include-dependencies",
            port.id,
        ],
    )

    # Verify migrated resources exist
    dest_network = test_destination_session.network.find_network(network.name)
    assert dest_network, "network was not migrated"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(dest_network.id)
    )

    dest_subnet = test_destination_session.network.find_subnet(subnet.name)
    assert dest_subnet, "subnet was not migrated"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(dest_subnet.id)
    )

    dest_sg = test_destination_session.network.find_security_group(security_group.name)
    assert dest_sg, "security group was not migrated"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_security_group(dest_sg.id)
    )

    # Find migrated port by network
    dest_ports = list(
        test_destination_session.network.ports(network_id=dest_network.id)
    )
    assert dest_ports, "port was not migrated"
    dest_port = dest_ports[0]
    request.addfinalizer(lambda: _delete_port(test_destination_session, dest_port.id))

    _check_migrated_port(port, dest_port)

    # Verify fixed IP was preserved and subnet_id was mapped
    assert dest_port.fixed_ips, "migrated port has no fixed IPs"
    assert len(dest_port.fixed_ips) == 1, "migrated port has wrong number of fixed IPs"
    assert dest_port.fixed_ips[0]["ip_address"] == "10.0.0.10", (
        "fixed IP address was not preserved"
    )
    assert dest_port.fixed_ips[0]["subnet_id"] == dest_subnet.id, (
        "fixed IP subnet_id was not mapped to migrated subnet"
    )
