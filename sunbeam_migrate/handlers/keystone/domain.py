# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from openstack import exceptions as openstack_exc

from sunbeam_migrate import exception
from sunbeam_migrate.handlers import base

LOG = logging.getLogger()


class DomainHandler(base.BaseMigrationHandler):
    """Handle Keystone domain migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "keystone"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return []

    def get_member_resource_types(self) -> list[str]:
        """Get a list of member (contained) resource types.

        The migrations can cascade to contained resources.
        """
        return ["project"]

    def get_member_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Get a list of member resources.

        Each entry will be a tuple containing the resource type and
        the resource id.
        """
        source_domain = self._source_session.identity.get_domain(resource_id)
        if not source_domain:
            raise exception.NotFound(f"Domain not found: {resource_id}")

        member_resources: list[tuple[str, str]] = []
        for project in self._source_session.identity.projects(
            domain_id=source_domain.id
        ):
            member_resources.append(("project", project.id))
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
        source_domain = self._source_session.identity.get_domain(resource_id)
        if not source_domain:
            raise exception.NotFound(f"Domain not found: {resource_id}")

        existing_domain = self._destination_session.identity.find_domain(
            source_domain.name, ignore_missing=True
        )
        if existing_domain:
            # TODO: we might consider moving those checks on the manager side
            # and have a consistent approach across handlers.
            LOG.warning(
                "Domain already exists: %s %s",
                existing_domain.id,
                existing_domain.name,
            )
            return existing_domain.id

        domain_kwargs = self._build_domain_kwargs(source_domain)
        destination_domain = self._destination_session.identity.create_domain(
            **domain_kwargs
        )

        return destination_domain.id

    def _build_domain_kwargs(self, source_domain) -> dict:
        """Build kwargs for creating a destination domain."""
        kwargs: dict = {}

        fields = [
            "name",
            "description",
            "enabled",
        ]
        for field in fields:
            value = getattr(source_domain, field, None)
            if value not in (None, {}):
                kwargs[field] = value

        return kwargs

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        resource_ids: list[str] = []
        for domain in self._source_session.identity.domains():
            resource_ids.append(domain.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        try:
            domain = openstack_session.identity.get_domain(resource_id)
            if domain and domain.is_enabled:
                # Domains must be disabled before deletion.
                openstack_session.identity.update_domain(domain, enabled=False)
        except openstack_exc.NotFoundException:
            pass

        openstack_session.identity.delete_domain(resource_id, ignore_missing=True)
