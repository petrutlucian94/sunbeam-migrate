# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from sunbeam_migrate import config, constants, exception
from sunbeam_migrate.db import api as db_api
from sunbeam_migrate.db import models
from sunbeam_migrate.handlers import base, factory

CONFIG = config.get_config()
LOG = logging.getLogger()


class SunbeamMigrationManager:
    def _get_migration_handler(
        self, resource_type: str | None
    ) -> base.BaseMigrationHandler:
        handler = factory.get_migration_handler(resource_type)
        handler.set_manager(self)
        return handler

    def perform_individual_migration(
        self,
        resource_type: str,
        resource_id: str,
        cleanup_source: bool = False,
        include_dependencies: bool = False,
        include_members: bool = False,
    ) -> models.Migration:
        """Migrate the specified resource."""
        handler = self._get_migration_handler(resource_type)

        if not resource_id:
            raise exception.InvalidInput("No resource id specified.")

        migration = self._migrate_parent_resource(
            handler=handler,
            resource_type=resource_type,
            resource_id=resource_id,
            cleanup_source=cleanup_source,
            include_dependencies=include_dependencies,
            include_members=include_members,
        )

        if include_members:
            migrated_member_resources = self._migrate_member_resources(
                handler=handler,
                resource_id=resource_id,
                cleanup_source=cleanup_source,
                include_dependencies=include_dependencies,
                include_members=include_members,
            )
            try:
                handler.connect_member_resources_to_parent(
                    parent_resource_id=migration.destination_id,
                    migrated_member_resources=migrated_member_resources,
                )
            except Exception as ex:
                LOG.error(
                    "Failed to connect member resources to parent %s: %r",
                    resource_id,
                    ex,
                )

        return migration

    def _migrate_parent_resource(
        self,
        handler,
        resource_type: str,
        resource_id: str,
        cleanup_source: bool,
        include_dependencies: bool,
        include_members: bool,
    ) -> models.Migration:
        """Handle the parent resource migration logic."""
        LOG.info("Initiating %s migration, resource id: %s", resource_type, resource_id)

        migration = models.Migration(
            service=handler.get_service_type(),
            source_cloud=CONFIG.source_cloud_name,
            destination_cloud=CONFIG.destination_cloud_name,
            source_id=resource_id,
            resource_type=resource_type,
            status=constants.STATUS_IN_PROGRESS,
        )
        migration.save()

        associated_migrations = []
        try:
            associated_resources = self._get_associated_resources(
                resource_type, resource_id
            )
            LOG.debug(
                "Associated resources of %s %s - %s",
                resource_type,
                resource_id,
                associated_resources,
            )
            if associated_resources["pending"]:
                if not include_dependencies:
                    raise exception.InvalidInput(
                        "The %s resource (%s) has pending associated resources. "
                        "Specify --include-dependencies to automatically migrate them "
                        "or use separate `sunbeam-migrate start` commands: %s"
                        % (resource_type, resource_id, associated_resources)
                    )
                for assoc_resource_type, assoc_resource_id in associated_resources[
                    "pending"
                ]:
                    # Check if this resource is already being migrated
                    existing = db_api.get_migrations(
                        source_id=assoc_resource_id,
                        resource_type=assoc_resource_type,
                    )
                    if existing:
                        if existing[0].status == constants.STATUS_COMPLETED:
                            LOG.info(
                                "Associated resource %s %s already completed"
                                " (migration %s), "
                                "skipping duplicate migration",
                                assoc_resource_type,
                                assoc_resource_id,
                                existing[0].uuid,
                            )
                            # Add it to associated_migrations for cleanup tracking
                            associated_migrations.append(existing[0])
                            continue
                        elif existing[0].status == constants.STATUS_IN_PROGRESS:
                            LOG.info(
                                "Associated resource %s %s already in progress"
                                " (migration %s), "
                                "will be available once migration completes",
                                assoc_resource_type,
                                assoc_resource_id,
                                existing[0].uuid,
                            )
                            continue

                    LOG.info(
                        "Migrating associated %s resource: %s",
                        assoc_resource_type,
                        assoc_resource_id,
                    )
                    associated_migration = self.perform_individual_migration(
                        assoc_resource_type,
                        assoc_resource_id,
                        include_dependencies=include_dependencies,
                        include_members=include_members,
                    )
                    associated_migrations.append(associated_migration)

                # Refresh the associated resources and ensure that all of them have
                # been migrated.
                associated_resources = self._get_associated_resources(
                    resource_type, resource_id
                )
                if associated_resources["pending"]:
                    raise exception.SunbeamMigrateException(
                        "Unable to migrate %s resource (%s), "
                        "dependencies still pending: %s"
                        % (resource_type, resource_id, associated_resources)
                    )

            # The handler is expected to cleanup failed migrations on the destination
            # side.
            destination_id = handler.perform_individual_migration(
                resource_id,
                migrated_associated_resources=associated_resources["migrated"],
            )
            migration.destination_id = destination_id

            # Mark the parent as successfully migrated *before* handling members
            # so that they can see it as an already-migrated dependency.
            migration.status = constants.STATUS_COMPLETED
            migration.save()

        except Exception as ex:
            migration.status = constants.STATUS_FAILED
            migration.error_message = "Migration failed, error: %r" % ex
            migration.save()
            raise

        if cleanup_source:
            self.cleanup_migration_source(migration)

            for associated_migration in associated_migrations:
                self.cleanup_migration_source(associated_migration)

        LOG.info(
            "Successfully migrated %s resource, destination id: %s",
            resource_type,
            destination_id,
        )
        migration.status = constants.STATUS_COMPLETED
        migration.destination_id = destination_id
        migration.save()

        return migration

    def _migrate_member_resources(
        self,
        handler,
        resource_id: str,
        cleanup_source: bool,
        include_dependencies: bool,
        include_members: bool,
    ) -> list[tuple[str, str, str]]:
        """Handle member resource migration logic."""
        migrated_member_resources: list[tuple[str, str, str]] = []
        member_resources = handler.get_member_resources(resource_id)
        for member_resource_type, member_resource_id in member_resources:
            # Check if this resource is already migrated or being migrated
            # (could have been migrated as an associated resource earlier)
            migrations = db_api.get_migrations(
                source_id=member_resource_id,
                resource_type=member_resource_type,
            )
            if migrations:
                latest = migrations[0]
                if latest.status == constants.STATUS_COMPLETED:
                    LOG.info(
                        "Member resource %s %s already completed (migration %s), "
                        "skipping duplicate migration",
                        member_resource_type,
                        member_resource_id,
                        latest.uuid,
                    )
                    continue
                elif latest.status == constants.STATUS_IN_PROGRESS:
                    LOG.info(
                        "Member resource %s %s already in progress (migration %s), "
                        "skipping duplicate migration",
                        member_resource_type,
                        member_resource_id,
                        latest.uuid,
                    )
                    continue
                # If status is FAILED, we'll retry by continuing below

            LOG.info(
                "Migrating member %s resource: %s",
                member_resource_type,
                member_resource_id,
            )
            try:
                migrated_member = self.perform_individual_migration(
                    member_resource_type,
                    member_resource_id,
                    cleanup_source=cleanup_source,
                    include_dependencies=include_dependencies,
                    include_members=include_members,
                )
                if (
                    migrated_member.resource_type
                    and migrated_member.source_id
                    and migrated_member.destination_id
                ):
                    migrated_member_resources.append(
                        (
                            migrated_member.resource_type,
                            migrated_member.source_id,
                            migrated_member.destination_id,
                        )
                    )
            except Exception as ex:
                LOG.error(
                    "Failed to migrate member resource %s %s: %r",
                    member_resource_type,
                    member_resource_id,
                    ex,
                )

        return migrated_member_resources

    def _get_associated_resources(
        self,
        resource_type: str,
        resource_id: str,
    ) -> dict[str, list[tuple]]:
        handler = self._get_migration_handler(resource_type)
        associated_resources = handler.get_associated_resources(resource_id)

        # TODO: let's define a Pydantic structure instead of this ugly list of tuples.
        migrated_resources: list[tuple[str, str, str]] = []
        pending_resources: list[tuple[str, str]] = []

        for resource_type, resource_id in associated_resources:
            migrations = db_api.get_migrations(
                source_id=resource_id, resource_type=resource_type
            )
            if not migrations or migrations[0].status != constants.STATUS_COMPLETED:
                pending_resources.append((resource_type, resource_id))
                continue
            else:
                migrated_resources.append(
                    (resource_type, resource_id, migrations[0].destination_id)
                )

        return {
            "migrated": migrated_resources,
            "pending": pending_resources,
        }

    def perform_batch_migration(
        self,
        resource_type: str,
        resource_filters: dict[str, str],
        dry_run: bool,
        cleanup_source: bool = False,
        include_dependencies: bool = False,
        include_members: bool = False,
    ):
        """Migrate multiple resources that match the specified filters."""
        handler = self._get_migration_handler(resource_type)

        resource_ids = handler.get_source_resource_ids(resource_filters)

        for resource_id in resource_ids:
            migrations = db_api.get_migrations(
                source_id=resource_id, status=constants.STATUS_COMPLETED
            )
            if migrations:
                LOG.info(
                    "Resource already migrated, skipping: %s. Migration: %s.",
                    resource_id,
                    migrations[-1].uuid,
                )
                continue

            if dry_run:
                LOG.info(
                    "DRY-RUN: %s migration, resource id: %s, cleanup source: %s",
                    resource_type,
                    resource_id,
                    cleanup_source,
                )
            else:
                self.perform_individual_migration(
                    resource_type,
                    resource_id,
                    cleanup_source=cleanup_source,
                    include_dependencies=include_dependencies,
                    include_members=include_members,
                )

    def cleanup_migration_source(self, migration: models.Migration):
        """Cleanup the migration source."""
        LOG.info(
            "Migration succeeded, cleaning up source %s: %s",
            migration.resource_type,
            migration.source_id,
        )
        if not migration.source_id:
            raise exception.InvalidInput("Missing source id.")

        try:
            handler = self._get_migration_handler(migration.resource_type)
            handler.delete_source_resource(migration.source_id)
            migration.source_removed = True
            migration.save()
        except Exception as ex:
            migration.status = constants.STATUS_SOURCE_CLEANUP_FAILED
            migration.error_message = "Source cleanup failed, error: %r" % ex
            migration.save()
            raise
