# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
import os
from typing import Any

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base

CONF = config.get_config()
LOG = logging.getLogger()


class InstanceHandler(base.BaseMigrationHandler):
    """Handle Nova instance migrations."""

    def get_service_type(self) -> str:
        """Return the Nova service type identifier."""
        return "nova"

    def get_supported_resource_filters(self) -> list[str]:
        """Return supported batch filters."""
        return ["owner_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types.

        Instances depend on image, security group, volume, flavor, keypair,
        network, and port, which must be migrated first.
        """
        return [
            "image",
            "security-group",
            "volume",
            "flavor",
            "keypair",
            "network",
            "port",
        ]

    def get_associated_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Return the source resources this instance depends on."""
        source_instance = self._source_session.compute.get_server(resource_id)
        if not source_instance:
            raise exception.NotFound(f"Instance not found: {resource_id}")

        associated_resources = []

        # Image
        #
        # Instances booted from image will be uploaded to Glance so that the
        # current VM data gets migrated. To accommodate scenarios that can start
        # with a fresh root disk, we may eventually add a setting called
        # "preserve_root_disk", allowing the original image to be used instead.
        #
        # if source_instance.image and source_instance.image.get("id"):
        #     associated_resources.append(("image", source_instance.image["id"]))

        # Flavor
        if source_instance.flavor and source_instance.flavor.get("id"):
            associated_resources.append(("flavor", source_instance.flavor["id"]))

        # Keypair
        if source_instance.key_name:
            keypair = self._source_session.compute.find_keypair(
                source_instance.key_name, ignore_missing=True
            )
            if keypair:
                associated_resources.append(("keypair", keypair.id))

        # Security groups
        security_groups = getattr(source_instance, "security_groups", None) or []
        for sg in security_groups:
            sg_id = sg.get("id") if isinstance(sg, dict) else getattr(sg, "id", None)
            if sg_id:
                associated_resources.append(("security-group", sg_id))

        # Volumes attached to the instance
        volumes_attached = getattr(source_instance, "volumes_attached", None) or []
        for volume in volumes_attached:
            volume_id = (
                volume.get("id")
                if isinstance(volume, dict)
                else getattr(volume, "id", None)
            )
            if volume_id:
                associated_resources.append(("volume", volume_id))

        # Ports attached to the instance
        for port in self._source_session.network.ports(device_id=source_instance.id):
            associated_resources.append(("port", port.id))

        return associated_resources

    def _upload_instance_to_image(self, source_instance):
        """Upload instance to Glance image."""
        rand = int.from_bytes(os.urandom(4))
        image_name = f"instmigr-{source_instance.id}-{rand}"
        LOG.info("Uploading instance %s to image: %s", source_instance.id, image_name)
        image = self._source_session.compute.create_image(
            source_instance.id, image_name
        )
        LOG.info("Waiting for instance upload to complete. Image id: %s", image.id)
        glance_image = self._source_session.get_image(image.id)
        self._source_session.image.wait_for_status(
            glance_image,
            status="active",
            failures=["error"],
            interval=5,
            wait=CONF.volume_upload_timeout,
        )
        LOG.info("Finished uploading instance to Glance.")
        return self._source_session.get_image(glance_image.id)

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
        source_instance = self._source_session.compute.get_server(resource_id)
        if not source_instance:
            raise exception.NotFound(f"Instance not found: {resource_id}")

        destination_image_id: str | None = None
        boot_volume_id: str | None = None
        source_image: Any = None

        # Handle image-booted instances: upload to Glance and migrate image
        if source_instance.image and source_instance.image.get("id"):
            source_image = self._upload_instance_to_image(source_instance)
            try:
                image_migration = self.manager.perform_individual_migration(
                    resource_type="image",
                    resource_id=source_image.id,
                    cleanup_source=True,
                )
                destination_image_id = image_migration.destination_id
            except Exception as ex:
                LOG.error("Failed to migrate instance image: %r", ex)
                # Clean up source image on error
                if source_image:
                    self._source_session.delete_image(
                        source_image.id, ignore_missing=True
                    )
                raise

        # Handle volume-booted instances
        if not destination_image_id and source_instance.volumes_attached:
            # Get the boot volume (typically the first one or one with boot_index=0)
            boot_volume = None
            for volume in source_instance.volumes_attached:
                volume_dict = volume if isinstance(volume, dict) else volume.to_dict()
                boot_index = volume_dict.get("boot_index", 0)
                if boot_index == 0:
                    boot_volume = volume_dict
                    break
            if not boot_volume and source_instance.volumes_attached:
                # Fallback to first volume if no boot_index found
                boot_volume = (
                    source_instance.volumes_attached[0]
                    if isinstance(source_instance.volumes_attached[0], dict)
                    else source_instance.volumes_attached[0].to_dict()
                )

            if boot_volume:
                volume_id = boot_volume.get("id")
                if volume_id:
                    boot_volume_id = self._get_associated_resource_destination_id(
                        "volume", volume_id, migrated_associated_resources
                    )

        try:
            # Build instance creation kwargs
            instance_kwargs = self._build_instance_kwargs(
                source_instance,
                destination_image_id,
                boot_volume_id,
                migrated_associated_resources,
            )

            # Create instance on destination
            destination_instance = self._destination_session.compute.create_server(
                **instance_kwargs
            )

            LOG.info("Waiting for instance provisioning: %s", destination_instance.id)
            self._destination_session.compute.wait_for_server(
                destination_instance,
                status="ACTIVE",
                failures=["ERROR"],
                interval=5,
                wait=CONF.resource_creation_timeout,
            )
        finally:
            # Clean up temporary images after instance is created
            if source_image:
                LOG.info("Deleting temporary image on source side: %s", source_image.id)
                self._source_session.delete_image(source_image.id, ignore_missing=True)

            if destination_image_id:
                LOG.info(
                    "Deleting temporary image on destination side: %s",
                    destination_image_id,
                )
                self._destination_session.delete_image(
                    destination_image_id, ignore_missing=True
                )

        return destination_instance.id

    # ruff: noqa: C901
    def _build_instance_kwargs(
        self,
        source_instance: Any,
        destination_image_id: str | None,
        boot_volume_id: str | None,
        migrated_associated_resources: list[tuple[str, str, str]],
    ) -> dict[str, Any]:
        """Build keyword arguments for creating an instance."""
        kwargs: dict[str, Any] = {
            "name": source_instance.name,
        }

        # Flavor
        if source_instance.flavor and source_instance.flavor.get("id"):
            dest_flavor_id = self._get_associated_resource_destination_id(
                "flavor",
                source_instance.flavor["id"],
                migrated_associated_resources,
            )
            kwargs["flavor_id"] = dest_flavor_id

        # Keypair
        if source_instance.key_name:
            dest_keypair_id = self._get_associated_resource_destination_id(
                "keypair",
                source_instance.key_name,  # Keypairs use name as ID
                migrated_associated_resources,
            )
            # Find keypair by ID to get the name
            dest_keypair = self._destination_session.compute.get_keypair(
                dest_keypair_id
            )
            kwargs["key_name"] = dest_keypair.name

        # Security groups
        security_groups = getattr(source_instance, "security_groups", None) or []
        destination_security_group_ids = []
        for sg in security_groups:
            sg_id = sg.get("id") if isinstance(sg, dict) else getattr(sg, "id", None)
            if sg_id:
                dest_sg_id = self._get_associated_resource_destination_id(
                    "security-group", sg_id, migrated_associated_resources
                )
                destination_security_group_ids.append(dest_sg_id)
        if destination_security_group_ids:
            kwargs["security_groups"] = destination_security_group_ids

        # Networks/Ports
        # Get ports attached to instance and map to destination ports
        destination_networks = []
        for port in self._source_session.network.ports(device_id=source_instance.id):
            dest_port_id = self._get_associated_resource_destination_id(
                "port", port.id, migrated_associated_resources
            )
            destination_networks.append({"port": dest_port_id})

        if destination_networks:
            kwargs["networks"] = destination_networks

        # Boot source: image or volume
        if destination_image_id:
            kwargs["image_id"] = destination_image_id
        elif boot_volume_id:
            kwargs["boot_volume"] = boot_volume_id
        else:
            raise exception.InvalidInput(
                "Instance must have either an image or boot volume"
            )

        # Additional volumes (non-boot)
        volumes_attached = getattr(source_instance, "volumes_attached", None) or []
        additional_volumes = []
        for volume in volumes_attached:
            volume_dict = volume if isinstance(volume, dict) else volume.to_dict()
            boot_index = volume_dict.get("boot_index", 0)
            if boot_index != 0:  # Not the boot volume
                volume_id = volume_dict.get("id")
                if volume_id:
                    dest_volume_id = self._get_associated_resource_destination_id(
                        "volume", volume_id, migrated_associated_resources
                    )
                    additional_volumes.append(dest_volume_id)
        if additional_volumes:
            kwargs["volumes"] = additional_volumes

        # Optional fields
        optional_fields = [
            "availability_zone",
            "metadata",
            "user_data",
            "config_drive",
            "description",
        ]
        if CONF.preserve_instance_availability_zone:
            optional_fields.append("availability_zone")

        for field in optional_fields:
            value = getattr(source_instance, field, None)
            if value is not None:
                kwargs[field] = value

        return kwargs

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Return all source instance ids."""
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "owner_id" in resource_filters:
            query_filters["project_id"] = resource_filters["owner_id"]

        resource_ids: list[str] = []
        for instance in self._source_session.compute.servers(**query_filters):
            resource_ids.append(instance.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.compute.delete_server(resource_id, ignore_missing=True)
