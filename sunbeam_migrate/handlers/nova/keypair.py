# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any

from sunbeam_migrate import exception
from sunbeam_migrate.handlers import base

LOG = logging.getLogger()


class KeypairHandler(base.BaseMigrationHandler):
    """Handle Nova keypair migrations."""

    def get_service_type(self) -> str:
        """Return the Nova service type identifier."""
        return "nova"

    def get_supported_resource_filters(self) -> list[str]:
        """Return supported batch filters."""
        # TODO: user id based filters.
        return []

    def perform_individual_migration(
        self,
        resource_id: str,
        migrated_associated_resources: list[base.MigratedResource],
    ) -> str:
        """Migrate a single keypair and return the destination id."""
        source_keypair = self._source_session.compute.get_keypair(resource_id)
        if not source_keypair:
            raise exception.NotFound(f"Keypair not found: {resource_id}")

        existing_keypair = self._destination_session.compute.find_keypair(
            source_keypair.name, ignore_missing=True
        )
        if existing_keypair:
            LOG.warning(
                "Keypair already exists: %s %s",
                existing_keypair.id,
                existing_keypair.name,
            )
            return existing_keypair.id

        keypair_kwargs = self._build_keypair_kwargs(source_keypair)
        destination_keypair = self._destination_session.compute.create_keypair(
            **keypair_kwargs
        )

        return destination_keypair.id

    def _build_keypair_kwargs(self, source_keypair: Any) -> dict[str, Any]:
        """Build keyword arguments for creating a keypair."""
        kwargs: dict[str, Any] = {
            "name": source_keypair.name,
            "public_key": source_keypair.public_key,
        }

        # Optional fields
        optional_fields = ["type"]
        for field in optional_fields:
            value = getattr(source_keypair, field, None)
            if value is not None:
                kwargs[field] = value

        # TODO: set the user id for cross-project (user) migrations.
        return kwargs

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Return all source keypair ids."""
        self._validate_resource_filters(resource_filters)

        resource_ids: list[str] = []
        for keypair in self._source_session.compute.keypairs():
            resource_ids.append(keypair.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.compute.delete_keypair(resource_id, ignore_missing=True)
