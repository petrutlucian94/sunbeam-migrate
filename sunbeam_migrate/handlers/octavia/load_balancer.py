# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base

CONF = config.get_config()
LOG = logging.getLogger(__name__)


class LoadBalancerHandler(base.BaseMigrationHandler):
    """Handle Octavia load balancer migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "octavia"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return ["project_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types.

        Associated resources must be migrated first.
        """
        types = ["network", "subnet", "floating-ip"]
        if CONF.multitenant_mode:
            types.append("project")
        return types

    def get_associated_resources(self, resource_id: str) -> list[base.Resource]:
        """Return the source resources this loadbalancer depends on."""
        source_load_balancer = self._source_session.load_balancer.get_load_balancer(
            resource_id
        )
        if not source_load_balancer:
            raise exception.NotFound(f"Load balancer not found: {resource_id}")

        associated_resources: list[base.Resource] = []
        self._report_identity_dependencies(
            associated_resources, project_id=source_load_balancer.project_id
        )

        if source_load_balancer.vip_subnet_id:
            associated_resources.append(
                base.Resource(
                    resource_type="subnet", source_id=source_load_balancer.vip_subnet_id
                )
            )
        if source_load_balancer.vip_network_id:
            associated_resources.append(
                base.Resource(
                    resource_type="network",
                    source_id=source_load_balancer.vip_network_id,
                )
            )

        # Collect member subnets from any default pools attached to listeners
        for listener in self._source_session.load_balancer.listeners(
            loadbalancer_id=resource_id
        ):
            default_pool_id = getattr(listener, "default_pool_id", None)
            if not default_pool_id:
                continue

            pool = self._source_session.load_balancer.get_pool(default_pool_id)
            if not pool:
                continue

            for member in self._source_session.load_balancer.members(pool.id):
                member_subnet_id = getattr(member, "subnet_id", None)
                if member_subnet_id:
                    associated_resources.append(
                        base.Resource(
                            resource_type="subnet", source_id=member_subnet_id
                        )
                    )

        # Collect any floating IPs associated with the load balancer's port
        source_lb_port_id = source_load_balancer.vip_port_id
        if source_lb_port_id:
            for floating_ip in self._source_session.network.ips(
                port_id=source_lb_port_id
            ):
                if floating_ip.id:
                    associated_resources.append(
                        base.Resource(
                            resource_type="floating-ip", source_id=floating_ip.id
                        )
                    )

        return associated_resources

    def get_member_resource_types(self) -> list[str]:
        """Get a list of member (contained) resource types.

        The migrations can cascade to contained resources.
        """
        return []

    # ruff: noqa: C901
    def perform_individual_migration(
        self,
        resource_id: str,
        migrated_associated_resources: list[base.MigratedResource],
    ) -> str:
        """Migrate the specified resource.

        :param resource_id: the resource to be migrated
        :param migrated_associated_resources: a list of MigratedResource
            objects describing migrated dependencies.

        Return the resulting resource id.
        """
        source_lb = self._source_session.load_balancer.get_load_balancer(resource_id)
        if not source_lb:
            raise exception.NotFound(f"Load balancer not found: {resource_id}")

        LOG.info("Gathering load balancer components from source: %s", resource_id)
        source_listeners = []
        source_pools_map = {}
        source_members_map = {}
        source_health_monitors_map = {}

        for listener in self._source_session.load_balancer.listeners(
            loadbalancer_id=resource_id
        ):
            source_listeners.append(listener)

        for listener in source_listeners:
            default_pool_id = listener.default_pool_id
            if default_pool_id and default_pool_id not in source_pools_map:
                pool = self._source_session.load_balancer.get_pool(default_pool_id)
                if pool:
                    source_pools_map[default_pool_id] = pool
                    # Get members for this pool
                    source_members_map[default_pool_id] = self._get_source_pool_members(
                        default_pool_id
                    )
                    # Get health monitor for this pool
                    if pool.health_monitor_id:
                        hm = self._source_session.load_balancer.get_health_monitor(
                            pool.health_monitor_id
                        )
                        if hm:
                            source_health_monitors_map[default_pool_id] = hm

        dest_lb_id = self._create_destination_load_balancer(
            source_lb, migrated_associated_resources
        )

        self._destination_session.load_balancer.wait_for_load_balancer(
            dest_lb_id,
            status="ACTIVE",
            failures=["ERROR"],
            interval=2,
            wait=CONF.resource_creation_timeout,
        )

        listener_id_map = {}
        pool_id_map = {}

        for source_listener in source_listeners:
            dest_listener_id = self._create_destination_listener(
                source_listener, dest_lb_id
            )
            listener_id_map[source_listener.id] = dest_listener_id

            self._destination_session.load_balancer.wait_for_load_balancer(
                dest_lb_id,
                status="ACTIVE",
                failures=["ERROR"],
                interval=2,
                wait=CONF.resource_creation_timeout,
            )

            if source_listener.default_pool_id:
                source_pool = source_pools_map.get(source_listener.default_pool_id)
                if source_pool and source_pool.id not in pool_id_map:
                    dest_pool_id = self._create_destination_pool(
                        source_pool, dest_listener_id
                    )
                    pool_id_map[source_pool.id] = dest_pool_id

                    self._destination_session.load_balancer.wait_for_load_balancer(
                        dest_lb_id,
                        status="ACTIVE",
                        failures=["ERROR"],
                        interval=2,
                        wait=CONF.resource_creation_timeout,
                    )

                    if source_pool.id in source_health_monitors_map:
                        source_hm = source_health_monitors_map[source_pool.id]
                        self._create_destination_health_monitor(source_hm, dest_pool_id)

                        self._destination_session.load_balancer.wait_for_load_balancer(
                            dest_lb_id,
                            status="ACTIVE",
                            failures=["ERROR"],
                            interval=2,
                            wait=CONF.resource_creation_timeout,
                        )

                    source_members = source_members_map.get(source_pool.id, [])
                    for source_member in source_members:
                        self._create_destination_member(
                            source_member,
                            dest_pool_id,
                            source_pool.id,
                            migrated_associated_resources,
                        )

                        self._destination_session.load_balancer.wait_for_load_balancer(
                            dest_lb_id,
                            status="ACTIVE",
                            failures=["ERROR"],
                            interval=2,
                            wait=CONF.resource_creation_timeout,
                        )

        # Attach Floating IPs to the destination load balancer port
        dest_lb = self._destination_session.load_balancer.get_load_balancer(dest_lb_id)
        if dest_lb.vip_port_id:
            for fip in self._source_session.network.ips(port_id=source_lb.vip_port_id):
                try:
                    dest_fip_id = self._get_associated_resource_destination_id(
                        "floating-ip",
                        fip.id,
                        migrated_associated_resources,
                    )
                except exception.NotFound:
                    LOG.warning(
                        "Floating IP %s not found in migrated associated resources, "
                        "skipping association with destination load balancer",
                        fip.id,
                    )
                    continue

                self._destination_session.network.update_ip(
                    dest_fip_id,
                    port_id=dest_lb.vip_port_id,
                )
                LOG.info(
                    "Associated floating IP %s (dest id: %s) to load balancer %s "
                    "on destination VIP port %s",
                    fip.floating_ip_address,
                    dest_fip_id,
                    dest_lb_id,
                    dest_lb.vip_port_id,
                )
        return dest_lb_id

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "project_id" in resource_filters:
            query_filters["project_id"] = resource_filters["project_id"]

        resource_ids = []
        for resource in self._source_session.load_balancer.load_balancers(
            **query_filters
        ):
            resource_ids.append(resource.id)

        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.load_balancer.delete_load_balancer(
            resource_id, ignore_missing=True, cascade=True
        )

    def _get_source_pool_members(self, pool_id: str) -> list:
        """Get all members for a source pool.

        :param pool_id: the source pool ID

        Return a list of member objects.
        """
        members = []
        for member in self._source_session.load_balancer.members(pool_id):
            members.append(member)
        return members

    def _create_destination_load_balancer(
        self,
        source_lb,
        migrated_associated_resources: list[base.MigratedResource],
    ) -> str:
        """Create a load balancer on the destination cloud.

        :param source_lb: the source load balancer object
        :param migrated_associated_resources: a list of MigratedResource
            objects describing migrated dependencies.

        Return the destination load balancer ID.
        """
        fields = [
            "name",
            "description",
            "is_admin_state_up",
            "flavor_id",
        ]
        if CONF.preserve_load_balancer_availability_zone:
            fields.append("availability_zone")

        kwargs = {}
        for field in fields:
            value = getattr(source_lb, field, None)
            if value is not None:
                kwargs[field] = value

        # Map the VIP subnet ID
        if source_lb.vip_subnet_id:
            kwargs["vip_subnet_id"] = self._get_associated_resource_destination_id(
                "subnet",
                source_lb.vip_subnet_id,
                migrated_associated_resources,
            )

        # Map the VIP network ID
        if source_lb.vip_network_id:
            kwargs["vip_network_id"] = self._get_associated_resource_destination_id(
                "network",
                source_lb.vip_network_id,
                migrated_associated_resources,
            )

        # Preserve VIP address
        if hasattr(source_lb, "vip_address") and source_lb.vip_address:
            kwargs["vip_address"] = source_lb.vip_address

        identity_kwargs = self._get_identity_build_kwargs(
            migrated_associated_resources,
            source_project_id=source_lb.project_id,
        )
        kwargs.update(identity_kwargs)

        dest_lb = self._destination_session.load_balancer.create_load_balancer(**kwargs)
        LOG.info(
            "Created load balancer %s on destination (source: %s)",
            dest_lb.id,
            source_lb.id,
        )
        return dest_lb.id

    def _create_destination_listener(self, source_listener, dest_lb_id: str) -> str:
        """Create a listener on the destination load balancer.

        :param source_listener: the source listener object
        :param dest_lb_id: the destination load balancer ID

        Return the destination listener ID.
        """
        fields = [
            "name",
            "description",
            "protocol",
            "protocol_port",
            "connection_limit",
            "is_admin_state_up",
            "default_tls_container_ref",
            "sni_container_refs",
            "insert_headers",
            "timeout_client_data",
            "timeout_member_connect",
            "timeout_member_data",
            "timeout_tcp_inspect",
            "allowed_cidrs",
        ]

        kwargs = {"loadbalancer_id": dest_lb_id}
        for field in fields:
            value = getattr(source_listener, field, None)
            if value is not None:
                kwargs[field] = value

        dest_listener = self._destination_session.load_balancer.create_listener(
            **kwargs
        )
        LOG.info(
            "Created listener %s on destination (source: %s)",
            dest_listener.id,
            source_listener.id,
        )
        return dest_listener.id

    def _create_destination_pool(self, source_pool, dest_listener_id: str) -> str:
        """Create a pool on the destination cloud.

        :param source_pool: the source pool object
        :param dest_listener_id: the destination listener ID

        Return the destination pool ID.
        """
        fields = [
            "name",
            "description",
            "protocol",
            "lb_algorithm",
            "is_admin_state_up",
            "session_persistence",
        ]

        kwargs = {"listener_id": dest_listener_id}
        for field in fields:
            value = getattr(source_pool, field, None)
            if value is not None:
                kwargs[field] = value

        dest_pool = self._destination_session.load_balancer.create_pool(**kwargs)
        LOG.info(
            "Created pool %s on destination (source: %s)",
            dest_pool.id,
            source_pool.id,
        )
        return dest_pool.id

    def _create_destination_member(
        self,
        source_member,
        dest_pool_id: str,
        source_pool_id: str,
        migrated_associated_resources: list[base.MigratedResource],
    ):
        """Create a pool member on the destination cloud.

        :param source_member: the source member object
        :param dest_pool_id: the destination pool ID
        :param source_pool_id: the source pool ID (for logging)
        :param migrated_associated_resources: a list of MigratedResource
            objects describing migrated dependencies.
        """
        fields = [
            "name",
            "address",
            "protocol_port",
            "weight",
            "is_admin_state_up",
            "monitor_address",
            "monitor_port",
            "backup",
        ]

        kwargs = {}
        for field in fields:
            value = getattr(source_member, field, None)
            if value is not None:
                kwargs[field] = value

        # Map subnet_id if present
        if hasattr(source_member, "subnet_id") and source_member.subnet_id:
            try:
                kwargs["subnet_id"] = self._get_associated_resource_destination_id(
                    "subnet",
                    source_member.subnet_id,
                    migrated_associated_resources,
                )
            except exception.NotFound:
                LOG.warning(
                    "Member subnet %s not found in migrated resources, "
                    "member may not work correctly",
                    source_member.subnet_id,
                )

        dest_member = self._destination_session.load_balancer.create_member(
            dest_pool_id, **kwargs
        )
        LOG.info(
            "Created member %s in pool %s on destination (source: %s)",
            dest_member.id,
            dest_pool_id,
            source_member.id,
        )

    def _create_destination_health_monitor(self, source_hm, dest_pool_id: str):
        """Create a health monitor on the destination cloud.

        :param source_hm: the source health monitor object
        :param dest_pool_id: the destination pool ID
        """
        fields = [
            "name",
            "type",
            "delay",
            "timeout",
            "max_retries",
            "max_retries_down",
            "http_method",
            "url_path",
            "expected_codes",
            "is_admin_state_up",
        ]

        kwargs = {"pool_id": dest_pool_id}
        for field in fields:
            value = getattr(source_hm, field, None)
            if value is not None:
                kwargs[field] = value

        dest_hm = self._destination_session.load_balancer.create_health_monitor(
            **kwargs
        )
        LOG.info(
            "Created health monitor %s on destination (source: %s)",
            dest_hm.id,
            source_hm.id,
        )
