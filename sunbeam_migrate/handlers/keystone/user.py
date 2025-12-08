# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from openstack import exceptions as openstack_exc

from sunbeam_migrate import exception
from sunbeam_migrate.handlers import base

LOG = logging.getLogger()


class UserHandler(base.BaseMigrationHandler):
    """Handle Keystone user migrations."""

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

        Users depend on domains.
        """
        return ["domain"]

    def get_associated_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Get a list of associated resources.

        Each entry will be a tuple containing the resource type and
        the resource id.
        """
        associated_resources = []

        source_user = self._source_session.identity.get_user(resource_id)
        if not source_user:
            raise exception.NotFound(f"User not found: {resource_id}")

        associated_resources.append(("domain", source_user.domain_id))

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
        source_user = self._source_session.identity.get_user(resource_id)
        if not source_user:
            raise exception.NotFound(f"User not found: {resource_id}")

        user_kwargs = self._build_user_kwargs(
            source_user, migrated_associated_resources
        )
        destination_user = self._destination_session.identity.create_user(**user_kwargs)

        return destination_user.id

    def _build_user_kwargs(
        self,
        source_user,
        migrated_associated_resources: list[tuple[str, str, str]],
    ) -> dict:
        """Build kwargs for creating a destination user."""
        kwargs: dict = {}

        fields = [
            "name",
            "description",
            "enabled",
            "email",
        ]
        for field in fields:
            value = getattr(source_user, field, None)
            if value not in (None, {}):
                kwargs[field] = value

        destination_domain_id = self._get_associated_resource_destination_id(
            "domain",
            source_user.domain_id,
            migrated_associated_resources,
        )
        kwargs["domain_id"] = destination_domain_id

        # Note: We don't migrate passwords for security reasons.
        # Users will need to reset their passwords on the destination.
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
        for user in self._source_session.identity.users(**query_params):
            resource_ids.append(user.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        try:
            user = openstack_session.identity.get_user(resource_id)
            if user and user.is_enabled:
                # Users must be disabled before deletion.
                openstack_session.identity.update_user(user, enabled=False)
        except openstack_exc.NotFoundException:
            pass

        openstack_session.identity.delete_user(resource_id, ignore_missing=True)
