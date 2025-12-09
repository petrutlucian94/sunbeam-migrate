# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils


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
