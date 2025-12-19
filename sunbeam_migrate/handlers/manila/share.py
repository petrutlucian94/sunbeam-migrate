# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
import subprocess
from typing import Any

from openstack import exceptions as openstack_exc

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base
from sunbeam_migrate.utils import client_utils, manila_utils

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
        return ["project_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types.

        Shares depend on share types.
        """
        types = ["share-type"]
        if CONF.multitenant_mode:
            types.append("project")
        return types

    def get_associated_resources(self, resource_id: str) -> list[base.Resource]:
        """Get a list of associated resources."""
        associated_resources: list[base.Resource] = []

        source_share = self._source_session.shared_file_system.get_share(resource_id)
        if not source_share:
            raise exception.NotFound(f"Share not found: {resource_id}")

        self._report_identity_dependencies(
            associated_resources, project_id=source_share.project_id
        )

        if source_share.share_type:
            associated_resources.append(
                base.Resource(
                    resource_type="share-type", source_id=source_share.share_type
                )
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

        identity_kwargs = self._get_identity_build_kwargs(
            migrated_associated_resources,
            source_project_id=source_share.project_id,
        )
        if CONF.multitenant_mode:
            owner_destination_session = self._owner_scoped_session(
                self._destination_session,
                [CONF.member_role_name],
                identity_kwargs["project_id"],
            )
        else:
            owner_destination_session = self._destination_session

        share_kwargs = self._build_share_kwargs(
            source_share, migrated_associated_resources
        )
        destination_share = owner_destination_session.shared_file_system.create_share(
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

        if CONF.preserve_share_access_rules:
            self._migrate_share_access_rules(
                source_share, destination_share, owner_destination_session
            )
        else:
            LOG.info("'preserve_share_access_rules' disabled.")

        self._migrate_share_data(source_share, destination_share)

        return destination_share.id

    def _build_share_kwargs(
        self,
        source_share,
        migrated_associated_resources: list[base.MigratedResource],
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

    def _migrate_share_access_rules(
        self, source_share, destination_share, destination_session
    ):
        """Migrate share access rules from source to destination share.

        :param source_share: The source share object
        :param destination_share: The destination share object
        :param destination_session: The session to use for destination operations
        """
        try:
            source_access_rules = self._source_session.shared_file_system.access_rules(
                source_share
            )
        except openstack_exc.NotFoundException:
            LOG.debug("No access rules found on source share: %s", source_share.id)
            return

        for rule in source_access_rules:
            # Skip rules that are not in active state
            if hasattr(rule, "state") and rule.state != "active":
                LOG.debug("Skipping access rule %s with state %s", rule.id, rule.state)
                continue

            try:
                LOG.info(
                    "Creating access rule on destination share %s: "
                    "type=%s, to=%s, level=%s",
                    destination_share.id,
                    rule.access_type,
                    rule.access_to,
                    rule.access_level,
                )
                access_rule = destination_session.shared_file_system.create_access_rule(
                    destination_share.id,
                    access_to=rule.access_to,
                    access_type=rule.access_type,
                    access_level=rule.access_level,
                )
                LOG.info("Waiting for access rule to become active: %s", access_rule.id)
                destination_session.shared_file_system.wait_for_status(
                    access_rule,
                    status="active",
                    attribute="state",
                    failures=["error"],
                    interval=5,
                    wait=CONF.resource_creation_timeout,
                )
            except openstack_exc.ConflictException as exc:
                LOG.warning(
                    "Access rule already exists or conflicts "
                    "on destination share %s: %r",
                    destination_share.id,
                    exc,
                )
            except Exception as exc:
                LOG.error(
                    "Failed to create access rule on destination share %s: %r",
                    destination_share.id,
                    exc,
                )
                # Continue with other rules even if one fails
                continue

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

    def get_source_resource_ids(self, resource_filters: dict[str, Any]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_params = {}
        if "project_id" in resource_filters:
            query_params["project_id"] = resource_filters["project_id"]
            query_params["all_tenants"] = True
            query_params["is_public"] = False

        resource_ids: list[str] = []

        source_manila = client_utils.get_manila_client(self._source_session)
        # The sdk filters seem broken, we'll use the native client.
        for share in source_manila.shares.list(search_opts=query_params):
            resource_ids.append(share.id)
        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.shared_file_system.delete_share(
            resource_id, ignore_missing=True
        )
