# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from manilaclient import exceptions as manila_exc

from sunbeam_migrate import exception
from sunbeam_migrate.handlers import base
from sunbeam_migrate.utils import client_utils

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
        source_manila = client_utils.get_manila_client(self._source_session)
        try:
            source_type = source_manila.share_types.get(resource_id)
        except manila_exc.NotFound:
            raise exception.NotFound(f"Share type not found: {resource_id}")

        dest_manila = client_utils.get_manila_client(self._destination_session)
        # Check if a share type with same name already exists.
        existing_types = [
            share_type
            for share_type in dest_manila.share_types.list()
            if share_type.name == source_type.name
        ]
        if existing_types:
            existing_type = existing_types[0]
            LOG.warning(
                "Share type already exists: %s %s",
                existing_type.id,
                existing_type.name,
            )
            return existing_type.id

        # For some reason we get a string instead of a boolean...
        dhss = source_type.required_extra_specs["driver_handles_share_servers"] in (
            "true",
            "True",
            True,
        )
        snapshot_support = source_type.extra_specs.get("snapshot_support") in (
            "true",
            "True",
            True,
        )
        destination_type = dest_manila.share_types.create(
            name=source_type.name,
            spec_driver_handles_share_servers=dhss,
            spec_snapshot_support=snapshot_support,
            is_public=source_type.is_public,
        )

        extra_specs = getattr(source_type, "extra_specs", None)
        if extra_specs:
            destination_type.set_keys(extra_specs)

        # TODO: handle type access
        return destination_type.id

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        source_manila = client_utils.get_manila_client(self._source_session)
        resource_ids: list[str] = []
        for share_type in source_manila.share_types.list():
            resource_ids.append(share_type.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        try:
            manila = client_utils.get_manila_client(openstack_session)
            manila.share_types.delete(resource_id)
        except manila_exc.NotFound:
            pass
        except Exception:
            # TODO: stop suppressing this once we include a flag along with
            # the resource dependencies, specifying which ones can be deleted.
            LOG.warning("Unable to delete share type, it's probably still in use.")
