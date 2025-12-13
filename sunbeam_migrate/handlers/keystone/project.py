# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from openstack import exceptions as openstack_exc

from sunbeam_migrate import exception
from sunbeam_migrate.handlers import base

LOG = logging.getLogger()


class ProjectHandler(base.BaseMigrationHandler):
    """Handle Keystone project migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "keystone"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return ["domain_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types.

        Projects depend on domains.
        """
        return ["domain"]

    def get_associated_resources(self, resource_id: str) -> list[base.Resource]:
        """Get a list of associated resources."""
        associated_resources = []

        source_project = self._source_session.identity.get_project(resource_id)
        if not source_project:
            raise exception.NotFound(f"Project not found: {resource_id}")

        associated_resources.append(
            base.Resource(resource_type="domain", source_id=source_project.domain_id)
        )
        return associated_resources

    def get_member_resource_types(self) -> list[str]:
        """Get a list of member (contained) resource types.

        The migrations can cascade to contained resources.
        """
        return ["user"]

    def get_member_resources(self, resource_id: str) -> list[base.Resource]:
        """Get a list of member resources."""
        source_project = self._source_session.identity.get_project(resource_id)
        if not source_project:
            raise exception.NotFound(f"Project not found: {resource_id}")

        member_resources: list[base.Resource] = []
        # Query users in the same domain as the project
        # Filter to only include users with default_project_id matching this project
        for user in self._source_session.identity.users(
            domain_id=source_project.domain_id
        ):
            if user.default_project_id == source_project.id:
                member_resources.append(
                    base.Resource(resource_type="user", source_id=user.id)
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
        source_project = self._source_session.identity.get_project(resource_id)
        if not source_project:
            raise exception.NotFound(f"Project not found: {resource_id}")

        destination_domain_id = self._get_associated_resource_destination_id(
            "domain",
            source_project.domain_id,
            migrated_associated_resources,
        )

        existing_project = self._destination_session.identity.find_project(
            source_project.name, domain_id=destination_domain_id
        )
        if existing_project:
            LOG.warning(
                "Project already exists: %s %s",
                existing_project.id,
                existing_project.name,
            )
            return existing_project.id

        project_kwargs = self._build_project_kwargs(
            source_project, destination_domain_id, migrated_associated_resources
        )
        destination_project = self._destination_session.identity.create_project(
            **project_kwargs
        )

        return destination_project.id

    def _build_project_kwargs(
        self,
        source_project,
        destination_domain_id: str,
        migrated_associated_resources: list[base.MigratedResource],
    ) -> dict:
        """Build kwargs for creating a destination project."""
        kwargs: dict = {}

        fields = [
            "name",
            "description",
            "enabled",
        ]
        for field in fields:
            value = getattr(source_project, field, None)
            if value not in (None, {}):
                kwargs[field] = value

        kwargs["domain_id"] = destination_domain_id

        return kwargs

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_params = {}
        if "domain_id" in resource_filters:
            query_params["domain_id"] = resource_filters["domain_id"]

        resource_ids: list[str] = []
        for project in self._source_session.identity.projects(**query_params):
            resource_ids.append(project.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        try:
            project = openstack_session.identity.get_project(resource_id)
            if project and project.is_enabled:
                # Projects must be disabled before deletion.
                openstack_session.identity.update_project(project, enabled=False)
        except openstack_exc.NotFoundException:
            pass

        openstack_session.identity.delete_project(resource_id, ignore_missing=True)
