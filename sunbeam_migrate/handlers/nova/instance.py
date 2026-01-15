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
        return ["project_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types."""
        types = [
            "image",
            "volume",
            "flavor",
            "keypair",
            "network",
            "port",
        ]
        if CONF.multitenant_mode:
            types.append("project")
        return types

    def get_associated_resources(self, resource_id: str) -> list[base.Resource]:
        """Return the source resources this instance depends on."""
        source_instance = self._source_session.compute.get_server(resource_id)
        if not source_instance:
            raise exception.NotFound(f"Instance not found: {resource_id}")

        associated_resources: list[base.Resource] = []
        self._report_identity_dependencies(
            associated_resources, project_id=source_instance.project_id
        )

        # Ports attached to the instance
        #
        # TODO: manually created ports are not deleted along with the instance.
        # However, it allows us to pass port settings that wouldn't be accessible
        # otherwise (e.g. port mac, vnic type, etc). That being considered, we should
        # have a config option, e.g. `migrate_instance_ports_individually`.
        #
        # Security groups will also have to be passed to the instance creation request
        # if we choose to no longer create ports manually.
        for port in self._source_session.network.ports(device_id=source_instance.id):
            associated_resources.append(
                base.Resource(
                    resource_type="port",
                    source_id=port.id,
                    should_cleanup=True,
                )
            )

        # Flavor
        source_flavor = self._source_session.compute.find_flavor(
            source_instance.flavor.id
        )
        associated_resources.append(
            base.Resource(resource_type="flavor", source_id=source_flavor.id)
        )

        # Keypair
        if CONF.multitenant_mode:
            LOG.warning("Keypair migration is not supported in multi-tenant mode.")
        else:
            if source_instance.key_name:
                keypair = self._source_session.compute.find_keypair(
                    source_instance.key_name, ignore_missing=False
                )
                associated_resources.append(
                    base.Resource(resource_type="keypair", source_id=keypair.id)
                )

        # Image
        #
        # Instances booted from image will be uploaded to Glance so that the
        # current VM data gets migrated. To accommodate scenarios that can start
        # with a fresh root disk, we may eventually add a setting called
        # "preserve_root_disk", allowing the original image to be used instead.
        #
        # if source_instance.image and source_instance.image.get("id"):
        #     associated_resources.append(
        #         base.Resource(
        #             resource_type="image",
        #             source_id=source_instance.image["id"]))

        # Volumes attached to the instance.
        #
        # Note that we're uploading the volumes to Glance in order to retrieve the
        # data. Cinder must be configured with `enable_force_upload = True` in order
        # to upload attached volumes.
        for volume in source_instance.attached_volumes or []:
            # TODO: set should_cleanup=False if the volume has multiple attachments.
            associated_resources.append(
                base.Resource(
                    resource_type="volume",
                    source_id=volume["id"],
                    should_cleanup=True,
                )
            )

        return associated_resources

    def _upload_instance_to_image(self, owner_source_session, source_instance):
        """Upload instance to Glance image."""
        rand = int.from_bytes(os.urandom(4))
        image_name = f"instmigr-{source_instance.id}-{rand}"
        LOG.info("Uploading instance %s to image: %s", source_instance.id, image_name)
        image = owner_source_session.compute.create_server_image(
            source_instance, image_name
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

    def _get_block_device_mapping(
        self,
        source_instance,
        migrated_associated_resources: list[base.MigratedResource],
    ) -> list[dict[str, Any]]:
        block_device_mapping = []
        for volume_attached in source_instance.attached_volumes or []:
            # Use the attachment API to retrieve more details.
            volume_id = volume_attached["id"]
            attachment = self._source_session.compute.get_volume_attachment(
                source_instance, volume_attached["id"]
            )

            dest_volume_id = self._get_associated_resource_destination_id(
                "volume", volume_id, migrated_associated_resources
            )

            mapping = {
                "delete_on_termination": attachment.delete_on_termination,
                "uuid": dest_volume_id,
                "source_type": "volume",
                "destination_type": "volume",
            }
            if attachment.tag:
                mapping["tag"] = attachment.tag
            if attachment.device in ("/dev/sda", "/dev/vda"):
                mapping["boot_index"] = 0

            block_device_mapping.append(mapping)
        return block_device_mapping

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
        source_instance = self._source_session.compute.get_server(resource_id)
        if not source_instance:
            raise exception.NotFound(f"Instance not found: {resource_id}")

        source_flavor = self._source_session.compute.find_flavor(
            source_instance.flavor.id
        )

        identity_kwargs = self._get_identity_build_kwargs(
            migrated_associated_resources,
            source_project_id=source_instance.project_id,
        )
        if CONF.multitenant_mode:
            owner_source_session = self._owner_scoped_session(
                self._source_session,
                [CONF.member_role_name],
                source_instance.project_id,
            )
            owner_destination_session = self._owner_scoped_session(
                self._destination_session,
                [CONF.member_role_name],
                identity_kwargs["project_id"],
            )
        else:
            owner_source_session = self._source_session
            owner_destination_session = self._destination_session

        destination_image_id: str | None = None
        source_image: Any = None

        # Handle image-booted instances: upload to Glance and migrate image
        if source_instance.image and source_instance.image.get("id"):
            source_image = self._upload_instance_to_image(
                owner_source_session, source_instance
            )
            try:
                image_migration = self.manager.perform_individual_migration(
                    resource_type="image",
                    resource_id=source_image.id,
                    cleanup_source=True,
                    include_dependencies=True,
                )
                destination_image_id = image_migration.destination_id
            except Exception as ex:
                LOG.error("Failed to migrate instance image: %r", ex)
                # Clean up source image on error
                if source_image:
                    self._source_session.image.delete_image(
                        source_image.id, ignore_missing=True
                    )
                raise

        try:
            # Build instance creation kwargs
            instance_kwargs = self._build_instance_kwargs(
                source_instance,
                source_flavor.id,
                destination_image_id,
                migrated_associated_resources,
            )

            # Create instance on destination
            destination_instance = owner_destination_session.compute.create_server(
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
                self._source_session.image.delete_image(
                    source_image.id, ignore_missing=True
                )

            if destination_image_id:
                LOG.info(
                    "Deleting temporary image on destination side: %s",
                    destination_image_id,
                )
                self._destination_session.image.delete_image(
                    destination_image_id, ignore_missing=True
                )

        return destination_instance.id

    # ruff: noqa: C901
    def _build_instance_kwargs(
        self,
        source_instance: Any,
        source_flavor_id: str,
        destination_image_id: str | None,
        migrated_associated_resources: list[base.MigratedResource],
    ) -> dict[str, Any]:
        """Build keyword arguments for creating an instance."""
        kwargs: dict[str, Any] = {
            "name": source_instance.name,
        }

        # Flavor
        dest_flavor_id = self._get_associated_resource_destination_id(
            "flavor",
            source_flavor_id,
            migrated_associated_resources,
        )
        kwargs["flavor_id"] = dest_flavor_id

        # Keypair
        if source_instance.key_name and not CONF.multitenant_mode:
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

        if destination_image_id:
            kwargs["image_id"] = destination_image_id

        block_device_mapping = self._get_block_device_mapping(
            source_instance, migrated_associated_resources
        )
        if block_device_mapping:
            kwargs["block_device_mapping_v2"] = block_device_mapping

        # Optional fields
        optional_fields = [
            "metadata",
            "user_data",
            "config_drive",
            "description",
        ]
        if CONF.preserve_instance_availability_zone:
            optional_fields.append("availability_zone")

        for field in optional_fields:
            value = getattr(source_instance, field, None)
            if value not in (None, ""):
                kwargs[field] = value

        return kwargs

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Return all source instance ids."""
        self._validate_resource_filters(resource_filters)

        query_filters: dict[str, Any] = {}
        if "project_id" in resource_filters:
            query_filters["project_id"] = resource_filters["project_id"]
            query_filters["all_tenants"] = True

        resource_ids: list[str] = []
        for instance in self._source_session.compute.servers(**query_filters):
            resource_ids.append(instance.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.compute.delete_server(resource_id, ignore_missing=True)
