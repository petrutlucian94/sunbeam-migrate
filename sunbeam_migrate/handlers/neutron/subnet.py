# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base

CONF = config.get_config()


class SubnetHandler(base.BaseMigrationHandler):
    """Handle Barbican secret container migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "neutron"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return ["owner_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types.

        Associated resources must be migrated first.
        """
        return ["network"]

    def get_associated_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Return the source resources this subnet depends on."""
        source_subnet = self._source_session.network.get_subnet(resource_id)
        if not source_subnet:
            raise exception.NotFound(f"Subnet not found: {resource_id}")

        associated_resources = []
        for network_ref in [source_subnet.network_id]:
            associated_resources.append(("network", network_ref))

        return associated_resources

    def get_member_resource_types(self) -> list[str]:
        """Get a list of member (contained) resource types.

        The migrations can cascade to contained resources.
        """
        return []

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
        source_subnet = self._source_session.network.get_subnet(resource_id)
        if not source_subnet:
            raise exception.NotFound(f"Subnet not found: {resource_id}")

        destination_network_id = self._get_associated_resource_destination_id(
            "network",
            source_subnet.network_id,
            migrated_associated_resources,
        )

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
        kwargs = {}
        for field in fields:
            value = getattr(source_subnet, field, None)
            if value is not None:
                kwargs[field] = value

        kwargs["network_id"] = destination_network_id

        destination_subnet = self._destination_session.network.create_subnet(**kwargs)
        return destination_subnet.id

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "owner" in resource_filters:
            query_filters["project_id"] = resource_filters["owner_id"]

        resource_ids = []
        for resource in self._source_session.network.subnets(**query_filters):
            resource_ids.append(resource.id)

        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.network.delete_subnet(resource_id, ignore_missing=True)
