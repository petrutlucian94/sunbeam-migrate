# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from openstack import exceptions as openstack_exc

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base

CONF = config.get_config()
LOG = logging.getLogger(__name__)


class RouterHandler(base.BaseMigrationHandler):
    """Handle Neutron router migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "neutron"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters."""
        return ["owner_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types.

        Associated resources must be migrated first.
        """
        return ["network", "subnet"]

    def get_associated_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Return the source resources this router depends on."""
        source_router = self._source_session.network.get_router(resource_id)
        if not source_router:
            raise exception.NotFound(f"Router not found: {resource_id}")

        associated_resources: list[tuple[str, str]] = []

        external_gateway_info = (
            getattr(source_router, "external_gateway_info", None) or {}
        )
        if not external_gateway_info:
            return associated_resources

        network_id = external_gateway_info.get("network_id")
        if network_id:
            associated_resources.append(("network", network_id))

            external_fixed_ips = external_gateway_info.get("external_fixed_ips") or []
            for fixed_ip in external_fixed_ips:
                if not fixed_ip:
                    continue
                subnet_id = fixed_ip.get("subnet_id")
                if subnet_id:
                    associated_resources.append(("subnet", subnet_id))

        return associated_resources

    def get_member_resource_types(self) -> list[str]:
        """Get a list of member (contained) resource types.

        The migrations can cascade to contained resources.
        """
        return ["subnet"]

    def get_member_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Return internal subnets connected to this router."""
        source_router = self._source_session.network.get_router(resource_id)
        if not source_router:
            raise exception.NotFound(f"Router not found: {resource_id}")

        member_subnet_ids = set()

        internal_owner_prefixes = (
            "network:router_interface",
            "network:router_interface_distributed",
            "network:ha_router_replicated_interface",
        )

        # Fetch all ports whose device_id == router.id
        for port in self._source_session.network.ports(device_id=source_router.id):
            owner = getattr(port, "device_owner", "") or ""
            if not any(owner.startswith(prefix) for prefix in internal_owner_prefixes):
                continue

            for ip in getattr(port, "fixed_ips", []) or []:
                subnet_id = ip.get("subnet_id")
                if subnet_id:
                    member_subnet_ids.add(subnet_id)

        member_resources = []
        for subnet_id in member_subnet_ids:
            member_resources.append(("subnet", subnet_id))

        return member_resources

    def perform_individual_migration(
        self,
        resource_id: str,
        migrated_associated_resources: list[tuple[str, str, str]],
    ) -> str:
        """Migrate the specified resource.

        :param resource_id: the resource to be migrated
        :param migrated_associated_resources: a list of tuples describing
            associated resources that have already been migrated.
            Format: (resource_type, source_id, destination_id)

        Return the resulting resource id.
        """
        source_router = self._source_session.network.get_router(resource_id)
        if not source_router:
            raise exception.NotFound(f"Router not found: {resource_id}")

        external_gateway_info = (
            getattr(source_router, "external_gateway_info", None) or {}
        )
        new_external_gateway_info = self._prepare_external_gateway_info(
            resource_id, external_gateway_info, migrated_associated_resources
        )

        fields = [
            "availability_zone_hints",
            "description",
            "flavor_id",
            "is_admin_state_up",
            "is_distributed",
            "is_ha",
            "name",
        ]

        kwargs = {}
        for field in fields:
            value = getattr(source_router, field, None)
            if value is not None:
                kwargs[field] = value

        if new_external_gateway_info is not None:
            kwargs["external_gateway_info"] = new_external_gateway_info

        destination_router = self._destination_session.network.create_router(**kwargs)
        return destination_router.id

    def connect_member_resources_to_parent(
        self,
        parent_resource_type: str,
        parent_resource_id: str | None,
        migrated_member_resources: list[tuple[str, str, str]],
    ):
        """Connect internal member subnets to the destination router."""
        for (
            resource_type,
            member_source_id,
            dest_subnet_id,
        ) in migrated_member_resources:
            if resource_type != "subnet":
                continue

            LOG.info(
                "Attaching internal subnet %s (dest %s) to router %s",
                member_source_id,
                dest_subnet_id,
                parent_resource_id,
            )

            try:
                self._destination_session.network.add_interface_to_router(
                    parent_resource_id,
                    subnet_id=dest_subnet_id,
                )
            except openstack_exc.ConflictException:
                LOG.debug(
                    "Interface for router %s on subnet %s already exists",
                    parent_resource_id,
                    dest_subnet_id,
                )

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "owner" in resource_filters:
            query_filters["project_id"] = resource_filters["owner"]

        resource_ids = []
        for resource in self._source_session.network.routers(**query_filters):
            resource_ids.append(resource.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.network.delete_router(resource_id, ignore_missing=True)

    def _prepare_external_gateway_info(
        self,
        resource_id: str,
        external_gateway_info: dict,
        migrated_associated_resources: list[tuple[str, str, str]],
    ) -> dict | None:
        """Prepare external gateway info for destination router.

        :param resource_id: the router resource ID being migrated
        :param external_gateway_info: the source router's external gateway info
        :param migrated_associated_resources: a list of tuples describing
            associated resources that have already been migrated.
            Format: (resource_type, source_id, destination_id)

        Return the prepared external gateway info dict or None.
        """
        if not external_gateway_info:
            return None

        new_external_gateway_info = dict(external_gateway_info)
        src_net_id = external_gateway_info.get("network_id")

        if src_net_id:
            external_gateway_network_id = self._get_associated_resource_destination_id(
                "network",
                src_net_id,
                migrated_associated_resources,
            )
            new_external_gateway_info["network_id"] = external_gateway_network_id

        original_fixed_ips = external_gateway_info.get("external_fixed_ips") or []
        new_fixed_ips = []

        for fixed_ip in original_fixed_ips:
            if not fixed_ip:
                continue
            src_subnet_id = fixed_ip.get("subnet_id")
            if not src_subnet_id:
                continue

            dest_subnet_id = self._get_associated_resource_destination_id(
                "subnet",
                src_subnet_id,
                migrated_associated_resources,
            )

            entry = {"subnet_id": dest_subnet_id}
            ip_address = fixed_ip.get("ip_address")
            if ip_address:
                entry["ip_address"] = ip_address
            new_fixed_ips.append(entry)

        new_external_gateway_info["external_fixed_ips"] = new_fixed_ips
        return new_external_gateway_info
