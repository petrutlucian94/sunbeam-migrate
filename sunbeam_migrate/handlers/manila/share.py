# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
import subprocess

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base
from sunbeam_migrate.utils import manila_utils

CONF = config.get_config()
LOG = logging.getLogger()


class ShareHandler(base.BaseMigrationHandler):
    """Handle Manila share migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "manila"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return ["owner_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types.

        Shares depend on share types.
        """
        return ["share-type"]

    def get_associated_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Get a list of associated resources.

        Each entry will be a tuple containing the resource type and
        the resource id.
        """
        associated_resources = []

        source_share = self._source_session.shared_file_system.get_share(resource_id)
        if not source_share:
            raise exception.NotFound(f"Share not found: {resource_id}")

        if source_share.share_type:
            associated_resources.append(("share-type", source_share.share_type))

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
        source_share = self._source_session.shared_file_system.get_share(resource_id)
        if not source_share:
            raise exception.NotFound(f"Share not found: {resource_id}")

        if source_share.share_protocol != "NFS":
            # Sunbeam only supports nfs, plus we'll need additional logic to
            # handle cephfs mounts.
            raise exception.InvalidInput(
                f"Unsupported share protocol: {source_share.share_protocol}, "
                f"share: {source_share.id}. "
                "NFS is the only supported share protocol at the moment."
            )

        share_kwargs = self._build_share_kwargs(
            source_share, migrated_associated_resources
        )
        destination_share = self._destination_session.shared_file_system.create_share(
            **share_kwargs
        )

        LOG.info("Waiting for share provisioning: %s", destination_share.id)
        self._destination_session.shared_file_system.wait_for_status(
            destination_share,
            status="available",
            failures=["error"],
            interval=5,
            wait=CONF.resource_creation_timeout,
        )

        self._migrate_share_data(source_share, destination_share)

        return destination_share.id

    def _build_share_kwargs(
        self,
        source_share,
        migrated_associated_resources: list[tuple[str, str, str]],
    ) -> dict:
        """Build kwargs for creating a destination share."""
        kwargs: dict = {}

        fields = [
            "name",
            "size",
            "share_protocol",
            "description",
            "is_public",
        ]
        for field in fields:
            value = getattr(source_share, field, None)
            if value not in (None, {}):
                kwargs[field] = value

        if source_share.share_type and CONF.preserve_share_type:
            destination_share_type_id = self._get_associated_resource_destination_id(
                "share-type",
                source_share.share_type,
                migrated_associated_resources,
            )
            kwargs["share_type"] = destination_share_type_id

        return kwargs

    def _migrate_share_data(self, source_share, destination_share):
        with (
            manila_utils.mounted_nfs_share(
                self._source_session, source_share
            ) as source_mountpoint,
            manila_utils.mounted_nfs_share(
                self._destination_session, destination_share
            ) as destination_mountpoint,
        ):
            LOG.info(
                "Migrating share data: %s -> %s",
                source_mountpoint,
                destination_mountpoint,
            )
            cmd = [
                "sudo",
                "cp",
                "-r",
                "--preserve=timestamps",
                "--preserve=xattr",
                "--preserve=links",
                "--preserve=ownership",
                f"{source_mountpoint}/.",
                f"{destination_mountpoint}/",
            ]
            subprocess.check_call(cmd, text=True)

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_params = {}
        if "owner_id" in resource_filters:
            query_params["project_id"] = resource_filters["owner_id"]

        resource_ids: list[str] = []
        for share in self._source_session.shared_file_system.shares(**query_params):
            resource_ids.append(share.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.shared_file_system.delete_share(
            resource_id, ignore_missing=True
        )
