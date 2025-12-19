# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from openstack import exceptions as openstack_exc

from sunbeam_migrate.tests.integration import utils as test_utils

LOG = logging.getLogger()


def create_test_network(session, is_router_external=False, **overrides):
    """Create a test network."""
    network_kwargs = {
        "name": test_utils.get_test_resource_name(),
        "is_router_external": is_router_external,
    }
    network_kwargs.update(overrides)
    network = session.network.create_network(**network_kwargs)
    # Refresh network information.
    return session.network.get_network(network.id)


def create_test_subnet(session, network, cidr="192.168.10.0/24", **overrides):
    """Create a test subnet."""
    subnet_kwargs = {
        "network_id": network.id,
        "ip_version": 4,
        "cidr": cidr,
        "name": test_utils.get_test_resource_name(),
    }
    subnet_kwargs.update(overrides)
    subnet = session.network.create_subnet(**subnet_kwargs)
    # Refresh subnet information.
    return session.network.get_subnet(subnet.id)


def create_test_security_group(session, **overrides):
    """Create a test security group."""
    sg_kwargs = {
        "name": test_utils.get_test_resource_name(),
        "description": "test security group",
    }
    sg_kwargs.update(overrides)
    sg = session.network.create_security_group(**sg_kwargs)
    # Refresh SG information.
    return session.network.get_security_group(sg.id)


def create_test_security_group_rule(session, security_group, **overrides):
    """Create a test security group rule."""
    rule_kwargs = {
        "security_group_id": security_group.id,
        "direction": "ingress",
        "ethertype": "IPv4",
        "protocol": "tcp",
        "port_range_min": 8080,
        "port_range_max": 8080,
    }
    rule_kwargs.update(overrides)
    rule = session.network.create_security_group_rule(**rule_kwargs)
    # Refresh rule information.
    return session.network.get_security_group_rule(rule.id)


def create_test_router(
    session, external_network=None, external_subnet=None, attach_subnet_id=None
):
    """Create a test router with optional external gateway and attached subnet."""
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
    if attach_subnet_id:
        session.network.add_interface_to_router(router, subnet_id=attach_subnet_id)
    return session.network.get_router(router.id)


def create_test_floating_ip(
    session, external_network_id: str, port_id: str, subnet_id: str | None
):
    kwargs = {
        "floating_network_id": external_network_id,
        "port_id": port_id,
        "description": "sunbeam-migrate test floating ip",
    }
    if subnet_id:
        kwargs["subnet_id"] = subnet_id
    floating_ip = session.network.create_ip(**kwargs)
    return session.network.get_ip(floating_ip.id)


def cleanup_router(session, router_id: str, subnet_id: str):
    try:
        session.network.remove_interface_from_router(router_id, subnet_id=subnet_id)
    except openstack_exc.NotFoundException:
        pass
    except Exception as exc:
        LOG.warning(
            "Failed removing interface from router %s for subnet %s: %s",
            router_id,
            subnet_id,
            exc,
        )

    try:
        session.network.update_router(router_id, external_gateway_info=None)
    except openstack_exc.NotFoundException:
        pass
    except Exception as exc:
        LOG.warning("Failed clearing gateway for router %s: %s", router_id, exc)

    try:
        session.network.delete_router(router_id, ignore_missing=True)
    except Exception as exc:
        LOG.warning("Failed deleting router %s: %s", router_id, exc)
