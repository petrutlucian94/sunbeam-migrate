# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import hashlib

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base

CONF = config.get_config()


class ImageHandler(base.BaseMigrationHandler):
    """Handle Glance image migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "glance"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return ["project_id"]

    def get_associated_resources(self, resource_id: str) -> list[base.Resource]:
        """Return the source resources this image depends on."""
        source_image = self._source_session.get_image(resource_id)
        if not source_image:
            raise exception.NotFound(f"Image not found: {resource_id}")

        associated_resources: list[base.Resource] = []
        self._report_identity_dependencies(
            associated_resources, project_id=source_image.owner_id
        )

        return associated_resources

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
        source_image = self._source_session.get_image(resource_id)
        if not source_image:
            raise exception.NotFound(f"Image not found: {resource_id}")

        # Basic properties
        fields = [
            "name",
            "container_format",
            "disk_format",
            "min_disk",
            "min_ram",
            "protected",
        ]
        # Extended properties
        fields += [
            "is_hidden",
            "is_protected",
            "hash_algo",
            "hash_value",
            "visibility",
            "architecture",
            "hypervisor_type",
            "instance_type_rxtx_factor",
            "instance_uuid",
            "needs_config_drive",
            "kernel_id",
            "os_distro",
            "os_version",
            "needs_secure_boot",
            "os_shutdown_timeout",
            "ramdisk_id",
            "vm_mode",
            "hw_cpu_sockets",
            "hw_cpu_cores",
            "hw_cpu_threads",
            "hw_disk_bus",
            "hw_cpu_policy",
            "hw_cpu_thread_policy",
            "hw_rng_model",
            "hw_machine_type",
            "hw_scsi_model",
            "hw_serial_port_count",
            "hw_video_model",
            "hw_video_ram",
            "hw_watchdog_action",
            "os_command_line",
            "hw_vif_model",
            "is_hw_vif_multiqueue_enabled",
            "is_hw_boot_menu_enabled",
            "vmware_adaptertype",
            "vmware_ostype",
            "has_auto_disk_config",
            "os_type",
            "os_admin_user",
            "hw_qemu_guest_agent",
            "os_require_quiesce",
        ]
        kwargs = {}
        for field in fields:
            value = getattr(source_image, field, None)
            if value:
                kwargs[field] = value

        identity_kwargs = self._get_identity_build_kwargs(
            migrated_associated_resources,
            source_project_id=source_image.owner_id,
            project_id_key="owner",
        )
        kwargs.update(identity_kwargs)

        destination_image = self._destination_session.create_image(
            data=self._chunked_image_reader(
                source_image, CONF.image_transfer_chunk_size
            ),
            **kwargs,
        )

        # Refresh the image to get all the information, including checksums.
        destination_image = self._destination_session.get_image(destination_image.id)
        if destination_image.checksum != source_image.checksum:
            raise exception.Invalid("Checksum mismatch in transferred image.")

        return destination_image.id

    def _chunked_image_reader(self, source_image, chunk_size: int):
        if not chunk_size:
            raise exception.InvalidInput("No image transfer chunk size provided.")
        response = self._source_session.image.download_image(source_image, stream=True)
        md5 = hashlib.md5(usedforsecurity=False)
        for chunk in response.iter_content(chunk_size=chunk_size):
            md5.update(chunk)
            yield chunk

        if md5.hexdigest() != response.headers["Content-MD5"]:
            raise exception.Invalid("Checksum mismatch in downloaded image.")

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "project_id" in resource_filters:
            query_filters["owner"] = resource_filters["project_id"]

        resource_ids = []
        for image in self._source_session.image.images(**query_filters):
            resource_ids.append(image.id)

        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.delete_image(resource_id)
