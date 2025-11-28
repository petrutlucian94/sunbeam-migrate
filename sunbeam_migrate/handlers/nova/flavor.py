# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from sunbeam_migrate import exception
from sunbeam_migrate.handlers import base


class FlavorHandler(base.BaseMigrationHandler):
    """Handle Nova flavor migrations."""

    def get_service_type(self) -> str:
        """Return the Nova service type identifier."""
        return "nova"

    def get_supported_resource_filters(self) -> list[str]:
        """Return supported batch filters."""
        return []

    def perform_individual_migration(
        self,
        resource_id: str,
        migrated_associated_resources: list[tuple[str, str, str]],
    ) -> str:
        """Migrate a single flavor and return the destination id."""
        source_flavor = self._source_session.compute.get_flavor(resource_id)
        if not source_flavor:
            raise exception.NotFound(f"Flavor not found: {resource_id}")

        existing_flavor = self._destination_session.compute.find_flavor(
            source_flavor.name, ignore_missing=True
        )
        if existing_flavor:
            return existing_flavor.id

        flavor_kwargs = self._build_flavor_kwargs(source_flavor)
        destination_flavor = self._destination_session.compute.create_flavor(
            **flavor_kwargs
        )

        extra_specs = getattr(source_flavor, "extra_specs", None) or {}
        if extra_specs:
            self._destination_session.compute.create_flavor_extra_specs(
                destination_flavor, **extra_specs
            )

        return destination_flavor.id

    def _build_flavor_kwargs(self, source_flavor: Any) -> dict[str, Any]:
        required_fields = ["ram", "vcpus", "disk"]
        for field in required_fields:
            if getattr(source_flavor, field, None) is None:
                raise exception.InvalidInput(f"Flavor {field} is missing.")

        kwargs: dict[str, Any] = {
            "name": source_flavor.name,
            "ram": source_flavor.ram,
            "vcpus": source_flavor.vcpus,
            "disk": source_flavor.disk,
        }

        optional_fields = [
            "swap",
            "ephemeral",
            "rxtx_factor",
            "is_public",
            "description",
        ]
        for field in optional_fields:
            value = getattr(source_flavor, field, None)
            if value not in (None, {}):
                kwargs[field] = value

        return kwargs

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Return all source flavor ids."""
        self._validate_resource_filters(resource_filters)

        resource_ids: list[str] = []
        for flavor in self._source_session.compute.flavors():
            resource_ids.append(flavor.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.compute.delete_flavor(resource_id, ignore_missing=True)
