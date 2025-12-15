# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base

CONF = config.get_config()


class NetworkHandler(base.BaseMigrationHandler):
    """Handle Barbican secret container migrations."""

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
        types = []
        if CONF.multitenant_mode:
            types.append("project")
        return types

    def get_associated_resources(self, resource_id: str) -> list[base.Resource]:
        """Return the source resources this network depends on."""
        source_network = self._source_session.network.get_network(resource_id)
        if not source_network:
            raise exception.NotFound(f"Network not found: {resource_id}")

        associated_resources: list[base.Resource] = []
        self._report_identity_dependencies(
            associated_resources, project_id=source_network.project_id
        )

        return associated_resources

    def get_member_resource_types(self) -> list[str]:
        """Get a list of member (contained) resource types.

        The migrations can cascade to contained resources.
        """
        return ["subnet"]

    def get_member_resources(self, resource_id: str) -> list[base.Resource]:
        """Return the subnets that belong to this network."""
        source_network = self._source_session.network.get_network(resource_id)
        if not source_network:
            raise exception.NotFound(f"Network not found: {resource_id}")

        member_resources: list[base.Resource] = []
        for subnet in self._source_session.network.subnets(
            network_id=source_network.id
        ):
            member_resources.append(
                base.Resource(resource_type="subnet", source_id=subnet.id)
            )
        return member_resources

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
        source_network = self._source_session.network.get_network(resource_id)
        if not source_network:
            raise exception.NotFound(f"Network not found: {resource_id}")

        fields = [
            "availability_zone_hints",
            "description",
            "dns_domain",
            "is_admin_state_up",
            "is_default",
            "is_port_security_enabled",
            "is_router_external",
            "is_shared",
            "mtu",
            "name",
            "provider_network_type",
            "provider_physical_network",
            "segments",
        ]
        if CONF.preserve_network_segmentation_id:
            fields.append("provider_segmentation_id")
        kwargs = {}
        for field in fields:
            value = getattr(source_network, field, None)
            if value:
                kwargs[field] = value

        identity_kwargs = self._get_identity_build_kwargs(
            migrated_associated_resources,
            source_project_id=source_network.project_id,
        )
        kwargs.update(identity_kwargs)

        dest_network = self._destination_session.network.create_network(**kwargs)

        return dest_network.id

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "project_id" in resource_filters:
            query_filters["project_id"] = resource_filters["project_id"]

        resource_ids = []
        for resource in self._source_session.network.networks(**query_filters):
            resource_ids.append(resource.id)

        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.network.delete_network(resource_id, ignore_missing=True)
