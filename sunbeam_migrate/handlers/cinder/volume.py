# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

"""
Cinder volume migration handler.

There are multiple ways in which an Openstack volume can be migrated:

1. Glance images
    * The volume gets uploaded to Glance, downloaded locally and uploaded
      to the destination Glance service. The volume then gets recreated using
      the Glance image.
    * Simplest approach and backend agnostic
    * Most inefficient
    * What we use right now.
2. Using the Cinder migration API
    * The backends must be part of the same Openstack cloud.
3. "os-brick"
    * The "os-brick" library can be used to connect the source and destination
      volumes locally, allowing the payload to be copied over (e.g. using dd).
    * Both storage backends must be accessible
    * May require additional packages and configuration (e.g. iSCSI initiator,
      Ceph client, etc).
4. Through backend specific mechanisms
    * Ceph RBD allows live migrating images between clusters.
5. In-place migration
    * Both clouds use the same external storage backend
    * It's a matter of importing the volume on the destination cloud.
"""

import logging
import os
from typing import Any

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base

CONF = config.get_config()
LOG = logging.getLogger()


class VolumeHandler(base.BaseMigrationHandler):
    """Handle Cinder volume type migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "cinder"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return ["owner_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types."""
        return ["volume-type"]

    def _get_source_volume_type_id(
        self,
        volume_id: str | None = None,
        volume_type_name: str | None = None,
    ):
        if not (volume_id or volume_type_name):
            raise exception.InvalidInput("No volume id or type name provided.")

        if not volume_type_name:
            source_volume = self._source_session.block_storage.get_volume(volume_id)
            if not source_volume:
                raise exception.NotFound(f"Volume not found: {volume_id}")

            volume_type_name = source_volume.volume_type

        volume_type = self._source_session.block_storage.find_type(
            volume_type_name, ignore_missing=False
        )
        return volume_type.id

    def get_associated_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Get a list of associated resources.

        Each entry will be a tuple containing the resource type and
        the resource id.
        """
        associated_resources = []

        if CONF.preserve_volume_type:
            volume_type_id = self._get_source_volume_type_id(volume_id=resource_id)
            associated_resources.append(("volume-type", volume_type_id))
        else:
            LOG.info(
                "'preserve_volume_type' disabled, the default volume type will be used."
            )

        return associated_resources

    def _upload_source_volume_to_image(self, source_volume):
        rand = int.from_bytes(os.urandom(4))
        image_name = f"volmigr-{source_volume.id}-{rand}"
        LOG.info("Uploading %s volume to image: %s", source_volume.id, image_name)
        response = self._source_session.block_storage.upload_volume_to_image(
            source_volume, image_name, force=True
        )
        image_id = response["image_id"]
        LOG.info("Waiting for volume upload to complete. Image id: %s", image_id)
        image = self._source_session.get_image(image_id)
        self._source_session.image.wait_for_status(
            image,
            status="active",
            failures=["error"],
            interval=5,
            wait=CONF.volume_upload_timeout,
        )
        LOG.info("Finished uploading source volume to Glance.")
        return self._source_session.get_image(image.id)

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
        source_volume = self._source_session.block_storage.get_volume(resource_id)
        if not source_volume:
            raise exception.NotFound(f"Volume not found: {resource_id}")

        source_image = self._upload_source_volume_to_image(source_volume)
        destination_image_id: str | None = None
        try:
            image_migration = self.manager.perform_individual_migration(
                resource_type="image", resource_id=source_image.id, cleanup_source=True
            )
            destination_image_id = image_migration.destination_id

            volume_kwargs = self._build_volume_kwargs(
                source_volume, destination_image_id, migrated_associated_resources
            )
            destination_volume = self._destination_session.block_storage.create_volume(
                **volume_kwargs
            )
            LOG.info("Waiting for volume provisioning: %s", destination_volume.id)
            self._destination_session.block_storage.wait_for_status(
                destination_volume,
                status="available",
                failures=["error"],
                interval=5,
                wait=CONF.volume_upload_timeout,
            )
        finally:
            LOG.info("Deleting temporary image on source side: %s", source_image.id)
            self._source_session.delete_image(source_image.id)
            if destination_image_id:
                LOG.info(
                    "Deleting temporary image on the destination side: %s",
                    destination_image_id,
                )
                self._destination_session.delete_image(destination_image_id)
            else:
                LOG.info(
                    "No image has been migrated as part of the volume transfer. "
                    "Skipping image cleanup..."
                )

        return destination_volume.id

    def _build_volume_kwargs(
        self,
        source_volume: Any,
        image_id: str | None,
        migrated_associated_resources: list[tuple[str, str, str]],
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}

        # Currently ignored fields:
        # * consistency/volume groups
        # * encryption keys
        # * Cinder managed replicas
        fields = [
            "description",
            "name",
            "is_multiattach",
            "size",
            "volume_image_metadata",
        ]
        if CONF.preserve_volume_availability_zone:
            fields.append("availability_zone")

        for field in fields:
            value = getattr(source_volume, field, None)
            if value not in (None, {}):
                kwargs[field] = value

        if CONF.preserve_volume_type:
            source_volume_type_id = self._get_source_volume_type_id(
                volume_type_name=source_volume.volume_type
            )
            destination_volume_type_id = self._get_associated_resource_destination_id(
                "volume-type", source_volume_type_id, migrated_associated_resources
            )
            kwargs["volume_type"] = destination_volume_type_id
        if image_id:
            kwargs["image_id"] = image_id

        return kwargs

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "owner_id" in resource_filters:
            query_filters["owner"] = resource_filters["owner_id"]

        resource_ids = []
        for volume in self._source_session.block_storage.volumes(**query_filters):
            resource_ids.append(volume.id)

        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.block_storage.delete_volume(resource_id, ignore_missing=True)
