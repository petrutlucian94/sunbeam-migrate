# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any

from manilaclient import client as manila_client
from manilaclient import exceptions as manila_exc

from sunbeam_migrate import exception
from sunbeam_migrate.handlers import base

LOG = logging.getLogger()


class ShareTypeHandler(base.BaseMigrationHandler):
    """Handle Manila share type migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "manila"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return []

    def _get_manila_client(self, openstack_session):
        """Get a manilaclient instance from an OpenStack SDK session."""
        # Use the session's auth to create a manila client
        return manila_client.Client("2", session=openstack_session.auth)

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
        source_manila = self._get_manila_client(self._source_session)
        try:
            source_type = source_manila.share_types.get(resource_id)
        except manila_exc.NotFound:
            raise exception.NotFound(f"Share type not found: {resource_id}")

        dest_manila = self._get_manila_client(self._destination_session)
        # Check if share type with same name already exists
        try:
            existing_types = dest_manila.share_types.list(
                search_opts={"name": source_type.name}
            )
            if existing_types:
                existing_type = existing_types[0]
                LOG.warning(
                    "Share type already exists: %s %s",
                    existing_type.id,
                    existing_type.name,
                )
                return existing_type.id
        except Exception:
            # If listing fails, continue with creation
            pass

        type_kwargs = self._build_type_kwargs(source_type)
        destination_type = dest_manila.share_types.create(**type_kwargs)

        extra_specs = getattr(source_type, "extra_specs", None)
        if extra_specs:
            dest_manila.share_types.set_keys(destination_type, extra_specs)

        # TODO: handle type access
        return destination_type.id

    def _build_type_kwargs(self, source_type: Any) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}

        fields = [
            "is_public",
            "description",
            "name",
        ]
        for field in fields:
            value = getattr(source_type, field, None)
            if value not in (None, {}):
                kwargs[field] = value

        return kwargs

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        source_manila = self._get_manila_client(self._source_session)
        resource_ids: list[str] = []
        for share_type in source_manila.share_types.list():
            resource_ids.append(share_type.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        try:
            manila = self._get_manila_client(openstack_session)
            manila.share_types.delete(resource_id)
        except manila_exc.NotFound:
            # Resource already deleted or doesn't exist
            pass
        except Exception:
            # TODO: stop suppressing this once we include a flag along with
            # the resource dependencies, specifying which ones can be deleted.
            LOG.warning("Unable to delete share type, it's probably still in use.")
