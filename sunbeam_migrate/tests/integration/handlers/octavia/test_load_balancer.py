# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from openstack import exceptions as openstack_exc

from sunbeam_migrate import config
from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.neutron import utils as neutron_utils

CONF = config.get_config()
LOG = logging.getLogger(__name__)


def _create_test_load_balancer(session, vip_subnet_id, vip_network_id):
    lb = session.load_balancer.create_load_balancer(
        name=test_utils.get_test_resource_name(),
        vip_subnet_id=vip_subnet_id,
        vip_network_id=vip_network_id,
    )

    return session.load_balancer.wait_for_load_balancer(
        lb.id,
        status="ACTIVE",
        failures=["ERROR"],
        interval=2,
        wait=CONF.resource_creation_timeout,
    )


def _create_test_listener(session, lb_id, protocol_port=80):
    listener = session.load_balancer.create_listener(
        name=test_utils.get_test_resource_name(),
        loadbalancer_id=lb_id,
        protocol="TCP",  # OVN provider supports TCP
        protocol_port=protocol_port,
    )

    session.load_balancer.wait_for_load_balancer(
        lb_id,
        status="ACTIVE",
        failures=["ERROR"],
        interval=2,
        wait=CONF.resource_creation_timeout,
    )
    return session.load_balancer.get_listener(listener.id)


def _create_test_pool(session, lb_id, listener_id):
    pool = session.load_balancer.create_pool(
        name=test_utils.get_test_resource_name(),
        listener_id=listener_id,
        loadbalancer_id=lb_id,
        protocol="TCP",
        lb_algorithm="SOURCE_IP_PORT",
    )

    session.load_balancer.wait_for_load_balancer(
        lb_id,
        status="ACTIVE",
        failures=["ERROR"],
        interval=2,
        wait=CONF.resource_creation_timeout,
    )
    return session.load_balancer.get_pool(pool.id)


def _create_test_member(session, lb, pool_id, address):
    subnet_id = lb.vip_subnet_id
    member = session.load_balancer.create_member(
        pool_id,
        name=test_utils.get_test_resource_name(),
        subnet_id=subnet_id,
        address=address,
        protocol_port=80,
    )
    session.load_balancer.wait_for_load_balancer(
        lb.id,
        status="ACTIVE",
        failures=["ERROR"],
        interval=2,
        wait=CONF.resource_creation_timeout,
    )
    return session.load_balancer.get_member(member.id, pool_id)


def _create_test_health_monitor(session, lb_id, pool_id):
    health_monitor = session.load_balancer.create_health_monitor(
        name=test_utils.get_test_resource_name(),
        pool_id=pool_id,
        type="TCP",
        delay=5,
        timeout=5,
        max_retries=3,
    )

    session.load_balancer.wait_for_load_balancer(
        lb_id,
        status="ACTIVE",
        failures=["ERROR"],
        interval=2,
        wait=CONF.resource_creation_timeout,
    )
    return session.load_balancer.get_health_monitor(health_monitor.id)


def _check_migrated_load_balancer(source_lb, destination_lb):
    fields = [
        "name",
        "description",
        "is_admin_state_up",
        "vip_address",
    ]
    for field in fields:
        source_attr = getattr(source_lb, field, None)
        dest_attr = getattr(destination_lb, field, None)
        assert source_attr == dest_attr, f"{field} attribute mismatch"


def _cleanup_destination_load_balancer(session, lb_id):
    """Best-effort removal of listeners, pools, members, then the LB itself."""
    lb = session.load_balancer.get_load_balancer(lb_id)
    if not lb:
        return

    session.load_balancer.wait_for_load_balancer(
        lb_id,
        status="ACTIVE",
        failures=["ERROR"],
        interval=2,
        wait=CONF.resource_creation_timeout,
    )

    for listener in session.load_balancer.listeners(loadbalancer_id=lb_id):
        pool_id = getattr(listener, "default_pool_id", None)
        if pool_id:
            pool = session.load_balancer.get_pool(pool_id)
            if pool:
                for member in session.load_balancer.members(pool.id):
                    try:
                        session.load_balancer.delete_member(
                            member.id, pool.id, ignore_missing=True
                        )
                        session.load_balancer.wait_for_load_balancer(
                            lb_id,
                            status="ACTIVE",
                            failures=["ERROR"],
                            interval=2,
                            wait=CONF.resource_creation_timeout,
                        )
                    except openstack_exc.NotFoundException:
                        pass
                    except Exception as exc:
                        LOG.warning(
                            "Failed deleting member %s from pool %s: %s",
                            getattr(member, "id", "<unknown>"),
                            pool.id,
                            exc,
                        )
                try:
                    session.load_balancer.delete_pool(pool.id, ignore_missing=True)
                    session.load_balancer.wait_for_load_balancer(
                        lb_id,
                        status="ACTIVE",
                        failures=["ERROR"],
                        interval=2,
                        wait=CONF.resource_creation_timeout,
                    )
                except openstack_exc.NotFoundException:
                    pass
                except Exception as exc:
                    LOG.warning(
                        "Failed deleting pool %s during cleanup: %s", pool.id, exc
                    )
        try:
            session.load_balancer.delete_listener(listener.id, ignore_missing=True)
            session.load_balancer.wait_for_load_balancer(
                lb_id,
                status="ACTIVE",
                failures=["ERROR"],
                interval=2,
                wait=CONF.resource_creation_timeout,
            )
        except openstack_exc.NotFoundException:
            pass
        except Exception as exc:
            LOG.warning(
                "Failed deleting listener %s during cleanup: %s",
                getattr(listener, "id", "<unknown>"),
                exc,
            )

    session.load_balancer.delete_load_balancer(lb_id, ignore_missing=True, cascade=True)
    try:
        session.load_balancer.wait_for_load_balancer(
            lb_id,
            status="DELETED",
            failures=["ERROR"],
            interval=2,
            wait=CONF.resource_creation_timeout,
        )
    except openstack_exc.NotFoundException:
        pass
    except Exception as exc:
        LOG.warning(
            "Failed waiting for load balancer %s deletion; resources may leak: %s",
            lb_id,
            exc,
        )


def _cleanup_ports(session, network_id: str):
    """Delete leftover neutron ports on the given network."""
    try:
        ports = list(session.network.ports(network_id=network_id))
    except openstack_exc.NotFoundException:
        return
    except Exception as exc:
        LOG.warning("Failed listing ports on network %s: %s", network_id, exc)
        return

    for port in ports:
        try:
            session.network.delete_port(port.id, ignore_missing=True)
        except openstack_exc.NotFoundException:
            pass
        except Exception as exc:
            LOG.warning(
                "Failed deleting port %s on network %s; may be leaked: %s",
                getattr(port, "id", "<unknown>"),
                network_id,
                exc,
            )


def _cleanup_router(session, router_id: str, subnet_id: str):
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


def _create_floating_ip_for_load_balancer(
    session, external_network_id: str, port_id: str, subnet_id: str | None
):
    kwargs = {
        "floating_network_id": external_network_id,
        "port_id": port_id,
        "description": "sunbeam-migrate load balancer floating ip test",
    }
    if subnet_id:
        kwargs["subnet_id"] = subnet_id
    floating_ip = session.network.create_ip(**kwargs)
    return session.network.get_ip(floating_ip.id)


def test_migrate_simple_load_balancer_and_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    # Create network and subnet for VIP
    network = neutron_utils.create_test_network(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_network(
            network.id, ignore_missing=True
        )
    )

    subnet = neutron_utils.create_test_subnet(
        test_source_session, network, cidr="11.11.10.0/24"
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_subnet(
            subnet.id, ignore_missing=True
        )
    )

    # Create load balancer
    lb = _create_test_load_balancer(test_source_session, subnet.id, network.id)
    request.addfinalizer(
        lambda: test_source_session.load_balancer.delete_load_balancer(
            lb.id, ignore_missing=True, cascade=True
        )
    )

    # Migrate load balancer with dependencies and cleanup source
    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=load-balancer",
            "--include-dependencies",
            "--cleanup-source",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    # Verify migrated load balancer
    dest_lb = test_destination_session.load_balancer.find_load_balancer(lb.name)
    assert dest_lb, "couldn't find migrated load balancer"

    _check_migrated_load_balancer(lb, dest_lb)

    # Verify cleanup on source
    assert not test_source_session.load_balancer.find_load_balancer(lb.id), (
        "cleanup-source didn't remove the load balancer"
    )

    # Get migrated subnet
    dest_subnet_id = test_utils.get_destination_resource_id(
        test_config_path, "subnet", subnet.id
    )
    dest_subnet = test_destination_session.network.get_subnet(dest_subnet_id)
    assert dest_subnet, "subnet not migrated"

    # Get migrated network
    dest_network_id = test_utils.get_destination_resource_id(
        test_config_path, "network", network.id
    )
    dest_network = test_destination_session.network.get_network(dest_network_id)
    assert dest_network, "network not migrated"

    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(
            dest_network_id, ignore_missing=True
        )
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(
            dest_subnet_id, ignore_missing=True
        )
    )
    request.addfinalizer(
        lambda: _cleanup_ports(test_destination_session, dest_network_id)
    )
    request.addfinalizer(
        lambda: _cleanup_destination_load_balancer(test_destination_session, dest_lb.id)
    )


def test_migrate_load_balancer_with_floating_ip_and_router(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    external_network = neutron_utils.create_test_network(
        test_source_session, is_router_external=True
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_network(
            external_network.id, ignore_missing=True
        )
    )

    external_subnet = neutron_utils.create_test_subnet(
        test_source_session, external_network, cidr="172.30.10.0/24"
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_subnet(
            external_subnet.id, ignore_missing=True
        )
    )

    network = neutron_utils.create_test_network(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_network(
            network.id, ignore_missing=True
        )
    )

    subnet = neutron_utils.create_test_subnet(
        test_source_session, network, cidr="11.11.10.0/24"
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_subnet(
            subnet.id, ignore_missing=True
        )
    )

    router = neutron_utils.create_test_router(
        test_source_session,
        external_network,
        external_subnet,
        attach_subnet_id=subnet.id,
    )
    request.addfinalizer(
        lambda: _cleanup_router(test_source_session, router.id, subnet.id)
    )

    lb = _create_test_load_balancer(test_source_session, subnet.id, network.id)
    request.addfinalizer(
        lambda: test_source_session.load_balancer.delete_load_balancer(
            lb.id, ignore_missing=True, cascade=True
        )
    )

    floating_ip = _create_floating_ip_for_load_balancer(
        test_source_session, external_network.id, lb.vip_port_id, external_subnet.id
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_ip(
            floating_ip.id, ignore_missing=True
        )
    )

    test_utils.call_migrate(
        test_config_path,
        [
            "start",
            "--resource-type=load-balancer",
            "--include-dependencies",
            lb.id,
        ],
    )

    dest_lb = test_destination_session.load_balancer.find_load_balancer(lb.name)
    assert dest_lb, "couldn't find migrated load balancer"
    _check_migrated_load_balancer(lb, dest_lb)

    dest_fip = test_destination_session.network.find_ip(floating_ip.floating_ip_address)
    assert dest_fip, "couldn't find migrated floating IP"
    assert dest_fip.port_id == dest_lb.vip_port_id, "floating IP not bound to VIP port"

    dest_network_id = test_utils.get_destination_resource_id(
        test_config_path, "network", network.id
    )
    dest_subnet_id = test_utils.get_destination_resource_id(
        test_config_path, "subnet", subnet.id
    )
    dest_external_network_id = test_utils.get_destination_resource_id(
        test_config_path, "network", external_network.id
    )
    dest_external_subnet_id = test_utils.get_destination_resource_id(
        test_config_path, "subnet", external_subnet.id
    )
    dest_router_id = test_utils.get_destination_resource_id(
        test_config_path, "router", router.id
    )
    dest_router = test_destination_session.network.get_router(dest_router_id)
    assert dest_router, "router dependency not migrated"

    gateway_info = getattr(dest_router, "external_gateway_info", {}) or {}
    assert gateway_info.get("network_id") == dest_external_network_id, (
        "router gateway not mapped to destination external network"
    )

    router_ports = list(
        test_destination_session.network.ports(
            device_id=dest_router.id, device_owner="network:router_interface"
        )
    )
    assert any(port.network_id == dest_network_id for port in router_ports), (
        "router is not attached to destination VIP network"
    )

    dest_lb_port = test_destination_session.network.get_port(dest_lb.vip_port_id)
    assert dest_lb_port, "destination load balancer VIP port missing"
    assert dest_lb_port.network_id == dest_network_id, (
        "VIP port not mapped to destination network"
    )
    assert dest_fip.floating_network_id == dest_external_network_id, (
        "floating network was not mapped to destination"
    )

    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(
            dest_external_network_id, ignore_missing=True
        )
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(
            dest_external_subnet_id, ignore_missing=True
        )
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(
            dest_network_id, ignore_missing=True
        )
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(
            dest_subnet_id, ignore_missing=True
        )
    )
    request.addfinalizer(
        lambda: _cleanup_router(
            test_destination_session, dest_router_id, dest_subnet_id
        )
    )
    request.addfinalizer(
        lambda: _cleanup_destination_load_balancer(test_destination_session, dest_lb.id)
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_ip(
            dest_fip.id, ignore_missing=True
        )
    )


def test_migrate_load_balancer_with_listener_pool_and_members(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    # Create network and subnet for VIP
    network = neutron_utils.create_test_network(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_network(
            network.id, ignore_missing=True
        )
    )

    subnet = neutron_utils.create_test_subnet(
        test_source_session, network, cidr="11.11.10.0/24"
    )
    request.addfinalizer(
        lambda: test_source_session.network.delete_subnet(
            subnet.id, ignore_missing=True
        )
    )

    # Create load balancer
    lb = _create_test_load_balancer(test_source_session, subnet.id, network.id)
    request.addfinalizer(
        lambda: test_source_session.load_balancer.delete_load_balancer(
            lb.id, ignore_missing=True, cascade=True
        )
    )

    # Create listener
    listener = _create_test_listener(test_source_session, lb.id, protocol_port=80)

    # Create pool
    pool = _create_test_pool(test_source_session, lb.id, listener.id)

    # Assign pool to listener
    test_source_session.load_balancer.update_listener(
        listener.id, default_pool_id=pool.id
    )

    # Create members
    _create_test_member(test_source_session, lb, pool.id, "11.11.10.10")
    _create_test_member(test_source_session, lb, pool.id, "11.11.10.11")

    # Create health monitor (may not be supported by OVN provider)
    health_monitor = _create_test_health_monitor(test_source_session, lb.id, pool.id)

    # Migrate load balancer with dependencies
    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=load-balancer",
            "--include-dependencies",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    # Verify migrated load balancer
    dest_lb = test_destination_session.load_balancer.find_load_balancer(lb.name)
    assert dest_lb, "couldn't find migrated load balancer"

    _check_migrated_load_balancer(lb, dest_lb)

    # Verify listener was migrated
    dest_listeners = list(
        test_destination_session.load_balancer.listeners(loadbalancer_id=dest_lb.id)
    )
    assert len(dest_listeners) == 1, "listener not migrated"
    dest_listener = dest_listeners[0]
    assert dest_listener.protocol == listener.protocol
    assert dest_listener.protocol_port == listener.protocol_port

    # Verify pool was migrated
    dest_pool = test_destination_session.load_balancer.find_pool(pool.name)
    assert dest_pool, "pool not migrated"
    assert dest_pool.protocol == pool.protocol
    assert dest_pool.lb_algorithm == pool.lb_algorithm

    # Verify members were migrated
    dest_members = list(test_destination_session.load_balancer.members(dest_pool.id))
    assert len(dest_members) == 2, "members not migrated"
    dest_addresses = {m.address for m in dest_members}
    assert "11.11.10.10" in dest_addresses
    assert "11.11.10.11" in dest_addresses

    # Verify health monitor was migrated (if supported)
    if health_monitor:
        assert dest_pool.health_monitor_id, "health monitor not migrated"
        dest_health_monitor = test_destination_session.load_balancer.get_health_monitor(
            dest_pool.health_monitor_id
        )
        assert dest_health_monitor.type == health_monitor.type
        assert dest_health_monitor.delay == health_monitor.delay
        assert dest_health_monitor.timeout == health_monitor.timeout
        assert dest_health_monitor.max_retries == health_monitor.max_retries

    # Get migrated subnet and network
    dest_subnet_id = test_utils.get_destination_resource_id(
        test_config_path, "subnet", subnet.id
    )
    dest_network_id = test_utils.get_destination_resource_id(
        test_config_path, "network", network.id
    )

    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(
            dest_network_id, ignore_missing=True
        )
    )
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(
            dest_subnet_id, ignore_missing=True
        )
    )
    request.addfinalizer(
        lambda: _cleanup_ports(test_destination_session, dest_network_id)
    )
    request.addfinalizer(
        lambda: _cleanup_destination_load_balancer(test_destination_session, dest_lb.id)
    )
