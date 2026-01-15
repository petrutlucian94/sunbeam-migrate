# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base

CONF = config.get_config()


class SubnetHandler(base.BaseMigrationHandler):
    """Handle Neutron subnet migrations."""

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
        types = ["network"]
        if CONF.multitenant_mode:
            types.append("project")
        return types

    def get_associated_resources(self, resource_id: str) -> list[base.Resource]:
        """Return the source resources this subnet depends on."""
        source_subnet = self._source_session.network.get_subnet(resource_id)
        if not source_subnet:
            raise exception.NotFound(f"Subnet not found: {resource_id}")

        associated_resources: list[base.Resource] = []
        self._report_identity_dependencies(
            associated_resources, project_id=source_subnet.project_id
        )
        associated_resources.append(
            base.Resource(resource_type="network", source_id=source_subnet.network_id)
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
        """Migrate the specified resource.

        :param resource_id: the resource to be migrated
        :param migrated_associated_resources: a list of MigratedResource
               objects describing migrated dependencies.

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
            # "subnet_pool_id",
            "use_default_subnet_pool",
        ]
        kwargs = {}
        for field in fields:
            value = getattr(source_subnet, field, None)
            if value is not None:
                kwargs[field] = value

        kwargs["network_id"] = destination_network_id

        identity_kwargs = self._get_identity_build_kwargs(
            migrated_associated_resources,
            source_project_id=source_subnet.project_id,
        )
        kwargs.update(identity_kwargs)

        # TODO: migrate subnet pools
        destination_subnet = self._destination_session.network.create_subnet(**kwargs)
        return destination_subnet.id

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "project_id" in resource_filters:
            query_filters["project_id"] = resource_filters["project_id"]

        resource_ids = []
        for resource in self._source_session.network.subnets(**query_filters):
            resource_ids.append(resource.id)

        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.network.delete_subnet(resource_id, ignore_missing=True)
