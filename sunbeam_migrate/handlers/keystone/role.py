# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from sunbeam_migrate import exception
from sunbeam_migrate.handlers import base

LOG = logging.getLogger()


class RoleHandler(base.BaseMigrationHandler):
    """Handle Keystone role migrations."""

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

        Roles can depend on domains if they are domain-specific.
        """
        return ["domain"]

    def get_associated_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Get a list of associated resources.

        Each entry will be a tuple containing the resource type and
        the resource id.
        """
        associated_resources = []

        source_role = self._source_session.identity.get_role(resource_id)
        if not source_role:
            raise exception.NotFound(f"Role not found: {resource_id}")

        # Roles can be domain-specific or global (domain_id can be None)
        if hasattr(source_role, "domain_id") and source_role.domain_id:
            associated_resources.append(("domain", source_role.domain_id))

        return associated_resources

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
        source_role = self._source_session.identity.get_role(resource_id)
        if not source_role:
            raise exception.NotFound(f"Role not found: {resource_id}")

        role_kwargs = self._build_role_kwargs(
            source_role, migrated_associated_resources
        )

        # When checking for existing role, include domain_id if present
        find_kwargs = {"name_or_id": source_role.name, "ignore_missing": True}
        if "domain_id" in role_kwargs:
            find_kwargs["domain_id"] = role_kwargs["domain_id"]

        existing_role = self._destination_session.identity.find_role(**find_kwargs)
        if existing_role:
            # TODO: we might consider moving those checks on the manager side
            # and have a consistent approach across handlers.
            LOG.warning(
                "Role already exists: %s %s",
                existing_role.id,
                existing_role.name,
            )
            return existing_role.id

        destination_role = self._destination_session.identity.create_role(**role_kwargs)

        return destination_role.id

    def _build_role_kwargs(
        self,
        source_role,
        migrated_associated_resources: list[tuple[str, str, str]],
    ) -> dict:
        """Build kwargs for creating a destination role."""
        kwargs: dict = {}

        fields = [
            "name",
            "description",
        ]
        for field in fields:
            value = getattr(source_role, field, None)
            if value not in (None, {}):
                kwargs[field] = value

        # Roles can be domain-specific or global (domain_id can be None)
        if hasattr(source_role, "domain_id") and source_role.domain_id:
            destination_domain_id = self._get_associated_resource_destination_id(
                "domain",
                source_role.domain_id,
                migrated_associated_resources,
            )
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
        for role in self._source_session.identity.roles(**query_params):
            resource_ids.append(role.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.identity.delete_role(resource_id, ignore_missing=True)
