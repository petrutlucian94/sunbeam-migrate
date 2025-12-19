# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import ipaddress
import logging

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base
from sunbeam_migrate.utils import neutron_utils

CONF = config.get_config()
LOG = logging.getLogger()


class FloatingIPHandler(base.BaseMigrationHandler):
    """Handle Neutron floating IP migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "neutron"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return ["project_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types.

        Associated resources must be migrated first.
        """
        types = ["network", "subnet", "router"]
        if CONF.multitenant_mode:
            types.append("project")
        return types

    def get_associated_resources(self, resource_id: str) -> list[base.Resource]:
        """Return the network and subnet this floating IP depends on."""
        source_fip = self._source_session.network.get_ip(resource_id)
        if not source_fip:
            raise exception.NotFound(f"Floating IP not found: {resource_id}")

        associated_resources: list[base.Resource] = []
        self._report_identity_dependencies(
            associated_resources, project_id=source_fip.project_id
        )

        floating_network_id = source_fip.floating_network_id
        if floating_network_id:
            associated_resources.append(
                base.Resource(resource_type="network", source_id=floating_network_id)
            )

        subnet_ids = set()
        if getattr(source_fip, "subnet_id", None):
            subnet_ids.add(source_fip.subnet_id)

        floating_ip = getattr(source_fip, "floating_ip_address", None)
        if floating_ip:
            try:
                floating_ip_addr = ipaddress.ip_address(floating_ip)
            except ValueError:
                LOG.error("Unable to parse FIP address: %s", floating_ip)
                floating_ip_addr = None

        if floating_ip_addr:
            for subnet in self._source_session.network.subnets(
                network_id=floating_network_id
            ):
                cidr = getattr(subnet, "cidr", None)
                if not cidr:
                    continue
                try:
                    network = ipaddress.ip_network(cidr, strict=False)
                except ValueError:
                    continue

                if floating_ip_addr in network:
                    # The Floating IP might not have a subnet_id set,
                    # but requires a subnet based on the IP address.
                    subnet_ids.add(subnet.id)
                    break
                else:
                    LOG.warning(
                        "Unable to find subnet for floating IP %s in network %s",
                        floating_ip,
                        floating_network_id,
                    )

        for subnet_id in sorted(subnet_ids):
            associated_resources.append(
                base.Resource(resource_type="subnet", source_id=subnet_id)
            )
        (router_id, router_subnet_id) = self._get_router_from_floating_ip(source_fip)
        if router_id and router_subnet_id:
            associated_resources.append(
                base.Resource(resource_type="router", source_id=router_id)
            )
            associated_resources.append(
                base.Resource(resource_type="subnet", source_id=router_subnet_id)
            )

        return associated_resources

    def get_member_resource_types(self) -> list[str]:
        """Get a list of member (contained) resource types.

        The migrations can cascade to contained resources.
        """
        return []

    def perform_individual_migration(
        self,
        resource_id: str,
        migrated_associated_resources: list[base.MigratedResource],
    ) -> str:
        """Migrate the specified floating IP.

        :param resource_id: the resource to be migrated
        :param migrated_associated_resources: a list of MigratedResource
            objects describing migrated dependencies.

        Return the resulting resource id.
        """
        source_fip = self._source_session.network.get_ip(resource_id)
        if not source_fip:
            raise exception.NotFound(f"Floating IP not found: {resource_id}")

        destination_network_id = self._get_associated_resource_destination_id(
            "network",
            source_fip.floating_network_id,
            migrated_associated_resources,
        )

        dest_subnet_id = None
        if source_fip.subnet_id:
            dest_subnet_id = self._get_associated_resource_destination_id(
                "subnet",
                source_fip.subnet_id,
                migrated_associated_resources,
            )

        fields = [
            "description",
            "dns_domain",
            "dns_name",
        ]
        if CONF.preserve_port_floating_ip_address:
            fields.append("floating_ip_address")

        kwargs = {}
        for field in fields:
            value = getattr(source_fip, field, None)
            if value is not None:
                kwargs[field] = value

        kwargs["floating_network_id"] = destination_network_id
        if dest_subnet_id:
            kwargs["subnet_id"] = dest_subnet_id
        (source_router_id, source_subnet_id) = self._get_router_from_floating_ip(
            source_fip
        )
        if source_router_id and source_subnet_id:
            try:
                dest_router_id = self._get_associated_resource_destination_id(
                    "router",
                    source_router_id,
                    migrated_associated_resources,
                )
                port_subnet_id = self._get_associated_resource_destination_id(
                    "subnet",
                    source_subnet_id,
                    migrated_associated_resources,
                )
                router_interface_subnets = neutron_utils.get_router_interface_subnets(
                    self._destination_session, dest_router_id
                )
                if port_subnet_id in router_interface_subnets:
                    LOG.info(
                        "Subnet %s already connected to router %s.",
                        port_subnet_id,
                        dest_router_id,
                    )
                else:
                    self._destination_session.network.add_interface_to_router(
                        dest_router_id,
                        subnet_id=port_subnet_id,
                    )
                    LOG.info(
                        "Added interface from subnet %s to router %s on destination "
                        "to allow floating IP association",
                        port_subnet_id,
                        dest_router_id,
                    )
            except exception.NotFound:
                LOG.warning(
                    "Router %s not found in migrated associated resources, "
                    "skipping interface addition on destination",
                    source_router_id,
                )

        identity_kwargs = self._get_identity_build_kwargs(
            migrated_associated_resources,
            source_project_id=source_fip.project_id,
        )
        kwargs.update(identity_kwargs)

        destination_fip = self._destination_session.network.create_ip(**kwargs)
        return destination_fip.id

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "project_id" in resource_filters:
            query_filters["project_id"] = resource_filters["project_id"]

        resource_ids = []
        for resource in self._source_session.network.ips(**query_filters):
            resource_ids.append(resource.id)

        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.network.delete_ip(resource_id, ignore_missing=True)

    def _get_router_from_floating_ip(
        self, floating_ip
    ) -> tuple[str | None, str | None]:
        """Get the router ID associated with a subnet.

        :param floating_ip: the floating IP object

        Return the router ID or None if not found.
        """
        # Get network id for the port from floating IP
        port_details = floating_ip.port_details or {}
        port_network_id = port_details.get("network_id")

        # Search for routers with interfaces on the subnets
        # of the port_network_id
        for router in self._source_session.network.routers():
            for port in self._source_session.network.ports(
                device_id=router.id,
                device_owner="network:router_interface",
            ):
                fixed_ips = getattr(port, "fixed_ips", None) or []
                for fixed_ip in fixed_ips:
                    subnet_id = fixed_ip.get("subnet_id")
                    subnet = self._source_session.network.get_subnet(subnet_id)
                    if subnet and subnet.network_id == port_network_id:
                        return (router.id, subnet_id)
        return (None, None)
