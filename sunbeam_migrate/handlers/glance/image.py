# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import hashlib

from sunbeam_migrate import config, constants, exception
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
        return ["owner_id"]

    def get_implementation_status(self) -> str:
        """Describe the implementation status."""
        return constants.IMPL_PARTIAL

    def perform_individual_migration(self, resource_id: str):
        """Migrate the specified resource.

        Return the resulting resource id.
        """
        source_image = self._source_session.get_image(resource_id)
        if not source_image:
            raise exception.NotFound(f"Image not found: {resource_id}")

        # TODO: pass the project name if the image belongs to a different tenant.
        # owner_project_name = source_image.location.project.name
        # destination_project_name = self._get_explicit_destination_project(
        #     owner_project_name
        # )

        # TODO: apply the other image properties.
        destination_image = self._destination_session.create_image(
            source_image.name,
            container=source_image.container_format,
            disk_format=source_image.disk_format,
            data=self._chunked_image_reader(
                source_image, CONF.image_transfer_chunk_size
            ),
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
        if "owner_id" in resource_filters:
            query_filters["owner"] = resource_filters["owner_id"]

        resource_ids = []
        for image in self._source_session.image.images(**query_filters):
            resource_ids.append(image.id)

        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.delete_image(resource_id)
