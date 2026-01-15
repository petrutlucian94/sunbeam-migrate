# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base

CONF = config.get_config()
LOG = logging.getLogger()


class SecurityGroupHandler(base.BaseMigrationHandler):
    """Handle Neutron security group migrations."""

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
        """Return the source resources this security group depends on."""
        source_sg = self._source_session.network.get_security_group(resource_id)
        if not source_sg:
            raise exception.NotFound(f"Security Group not found: {resource_id}")

        associated_resources: list[base.Resource] = []
        self._report_identity_dependencies(
            associated_resources, project_id=source_sg.project_id
        )

        return associated_resources

    def get_member_resource_types(self) -> list[str]:
        """Get a list of member (contained) resource types.

        The migrations can cascade to contained resources.
        """
        return ["security-group-rule"]

    def get_member_resources(self, resource_id: str) -> list[base.Resource]:
        """Return the rules belonging to this security group."""
        source_sg = self._source_session.network.get_security_group(resource_id)
        if not source_sg:
            raise exception.NotFound(f"Security Group not found: {resource_id}")

        member_resources: list[base.Resource] = []
        for rule in self._source_session.network.security_group_rules(
            security_group_id=source_sg.id
        ):
            member_resources.append(
                base.Resource(resource_type="security-group-rule", source_id=rule.id)
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
        source_sg = self._source_session.network.get_security_group(resource_id)
        if not source_sg:
            raise exception.NotFound(f"Security Group not found: {resource_id}")

        identity_kwargs = self._get_identity_build_kwargs(
            migrated_associated_resources,
            source_project_id=source_sg.project_id,
        )

        if source_sg.name == "default":
            destination_sg = self._destination_session.network.find_security_group(
                "default", **identity_kwargs
            )
            if destination_sg:
                LOG.info("Skipped recreating default security group.")
                return destination_sg.id

        fields = ["description", "name", "stateful"]
        kwargs = {}
        for field in fields:
            value = getattr(source_sg, field, None)
            if value is not None:
                kwargs[field] = value

        kwargs.update(identity_kwargs)

        dest_sg = self._destination_session.network.create_security_group(**kwargs)
        return dest_sg.id

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "project_id" in resource_filters:
            query_filters["project_id"] = resource_filters["project_id"]

        source_security_groups = self._source_session.network.security_groups(
            **query_filters
        )
        return [sg.id for sg in source_security_groups]

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.network.delete_security_group(
            resource_id, ignore_missing=True
        )
