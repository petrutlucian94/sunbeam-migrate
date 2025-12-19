# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
import typing

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
        dry_run: bool = False,
    ) -> models.Migration:
        """Migrate the specified resource."""
        if dry_run:
            return self._perform_individual_migration_dry_run(
                resource_type,
                resource_id,
                cleanup_source=cleanup_source,
                include_dependencies=include_dependencies,
                include_members=include_members,
            )

        handler = self._get_migration_handler(resource_type)

        if not resource_id:
            raise exception.InvalidInput("No resource id specified.")

        migration, associated_migrations = self._migrate_parent_resource(
            handler=handler,
            resource_type=resource_type,
            resource_id=resource_id,
            include_dependencies=include_dependencies,
            include_members=include_members,
        )

        migration.status = constants.STATUS_PENDING_MEMBERS
        migration.save()

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

        if cleanup_source:
            migration.status = constants.STATUS_PENDING_CLEANUP
            migration.save()

            self.cleanup_migration_source(migration)

            for associated_migration in associated_migrations:
                self.cleanup_migration_source(associated_migration)

        migration.status = constants.STATUS_COMPLETED
        migration.save()
        return migration

    def _migrate_parent_resource(
        self,
        handler,
        resource_type: str,
        resource_id: str,
        include_dependencies: bool,
        include_members: bool,
    ) -> tuple[models.Migration, list[models.Migration]]:
        """Handle the parent resource migration logic.

        Returns a migration object for the requested resource and a list of
        associated (dependency) migrations that can be cleaned up.
        """
        existing = db_api.get_migrations(
            source_id=resource_id,
            resource_type=resource_type,
        )
        if existing and existing[0].status in constants.LIST_STATUS_MIGRATED:
            LOG.info(
                "Already migrated %s resource: %s (migration %s, status %s) "
                "skipping duplicate migration",
                resource_type,
                resource_id,
                existing[0].uuid,
                existing[0].status,
            )
            return existing[0], []

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

        cleanup_associated_migrations = []
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
                for associated_resource in associated_resources["pending"]:
                    # Check if this resource is already being migrated
                    existing = db_api.get_migrations(
                        source_id=associated_resource.source_id,
                        resource_type=associated_resource.resource_type,
                    )
                    if existing:
                        if existing[0].status in constants.LIST_STATUS_MIGRATED:
                            LOG.info(
                                "Associated resource %s %s already completed"
                                " (migration %s, status %s), "
                                "skipping duplicate migration",
                                associated_resource.resource_type,
                                associated_resource.source_id,
                                existing[0].uuid,
                                existing[0].status,
                            )
                            continue
                        elif existing[0].status == constants.STATUS_IN_PROGRESS:
                            LOG.info(
                                "Associated resource %s %s already in progress"
                                " (migration %s), "
                                "will be available once migration completes",
                                associated_resource.resource_type,
                                associated_resource.source_id,
                                existing[0].uuid,
                            )
                            continue

                    LOG.info(
                        "Migrating associated %s resource: %s",
                        associated_resource.resource_type,
                        associated_resource.source_id,
                    )
                    associated_migration = self.perform_individual_migration(
                        associated_resource.resource_type,
                        associated_resource.source_id,
                        include_dependencies=include_dependencies,
                        include_members=include_members,
                    )
                    # Indirect dependencies will not be included.
                    if associated_resource.should_cleanup:
                        LOG.debug(
                            "Adding associated resource to the cleanup list: %s",
                            associated_resource,
                        )
                        cleanup_associated_migrations.append(associated_migration)
                    else:
                        LOG.debug(
                            "The associated resource should not be cleaned up: %s, "
                            "it may be shared with other resources.",
                            associated_resource,
                        )

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
            migration.save()
        except Exception as ex:
            migration.status = constants.STATUS_FAILED
            migration.error_message = "Migration failed, error: %r" % ex
            migration.save()
            raise

        LOG.info(
            "Successfully migrated %s resource, destination id: %s",
            resource_type,
            destination_id,
        )

        return migration, cleanup_associated_migrations

    def _migrate_member_resources(
        self,
        handler,
        resource_id: str,
        cleanup_source: bool,
        include_dependencies: bool,
        include_members: bool,
    ) -> list[base.MigratedResource]:
        """Handle member resource migration logic."""
        migrated_member_resources: list[base.MigratedResource] = []
        member_resources = handler.get_member_resources(resource_id)
        for member_resource in member_resources:
            # Check if this resource is already migrated or being migrated
            # (could have been migrated as an associated resource earlier)
            migrations = db_api.get_migrations(
                source_id=member_resource.source_id,
                resource_type=member_resource.resource_type,
            )
            if migrations:
                latest = migrations[0]
                if latest.status in constants.LIST_STATUS_MIGRATED:
                    LOG.info(
                        "Member resource %s %s already completed (migration %s - %s), "
                        "skipping duplicate migration",
                        member_resource.resource_type,
                        member_resource.source_id,
                        latest.uuid,
                        latest.status,
                    )
                    continue
                elif latest.status == constants.STATUS_IN_PROGRESS:
                    LOG.info(
                        "Member resource %s %s already in progress (migration %s), "
                        "skipping duplicate migration",
                        member_resource.resource_type,
                        member_resource.source_id,
                        latest.uuid,
                    )
                    continue
                # If status is FAILED, we'll retry by continuing below

            LOG.info(
                "Migrating member %s resource: %s",
                member_resource.resource_type,
                member_resource.source_id,
            )
            try:
                migrated_member = self.perform_individual_migration(
                    member_resource.resource_type,
                    member_resource.source_id,
                    cleanup_source=cleanup_source,
                    include_dependencies=include_dependencies,
                    include_members=include_members,
                )
                migrated_member_resources.append(
                    self._get_migrated_resource(migrated_member)
                )
            except Exception as ex:
                LOG.error(
                    "Failed to migrate member resource %s %s: %r",
                    member_resource.resource_type,
                    member_resource.source_id,
                    ex,
                )

        return migrated_member_resources

    def _get_associated_resources(
        self,
        resource_type: str,
        resource_id: str,
    ) -> dict[str, typing.Sequence[base.Resource]]:
        handler = self._get_migration_handler(resource_type)
        associated_resources = handler.get_associated_resources(resource_id)

        migrated_resources: list[base.MigratedResource] = []
        pending_resources: list[base.Resource] = []

        for associated_resource in associated_resources:
            migrations = db_api.get_migrations(
                source_id=associated_resource.source_id,
                resource_type=associated_resource.resource_type,
            )
            if not migrations:
                pending_resources.append(associated_resource)
            elif migrations[0].status not in constants.LIST_STATUS_MIGRATED:
                pending_resources.append(associated_resource)
            else:
                migrated_resources.append(self._get_migrated_resource(migrations[0]))

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

            self.perform_individual_migration(
                resource_type,
                resource_id,
                cleanup_source=cleanup_source,
                include_dependencies=include_dependencies,
                include_members=include_members,
                dry_run=dry_run,
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

    def _get_migrated_resource(
        self, migration: models.Migration
    ) -> base.MigratedResource:
        required_fields = ["resource_type", "source_id", "destination_id"]
        for field in required_fields:
            if not getattr(migration, field, None):
                raise exception.InvalidInput(f"Missing migration {field}.")
        return base.MigratedResource(
            resource_type=str(migration.resource_type),
            source_id=str(migration.source_id),
            destination_id=str(migration.destination_id),
        )

    def _perform_individual_migration_dry_run(
        self,
        resource_type: str,
        resource_id: str,
        cleanup_source: bool = False,
        include_dependencies: bool = False,
        include_members: bool = False,
    ) -> models.Migration:
        handler = self._get_migration_handler(resource_type)

        if not resource_id:
            raise exception.InvalidInput("No resource id specified.")

        existing = db_api.get_migrations(
            source_id=resource_id,
            resource_type=resource_type,
        )
        if existing and existing[0].status in constants.LIST_STATUS_MIGRATED:
            LOG.info(
                "Already migrated %s resource: %s (migration %s, status %s) "
                "skipping duplicate migration",
                resource_type,
                resource_id,
                existing[0].uuid,
                existing[0].status,
            )
            return existing[0]

        LOG.info(
            "DRY-RUN: migrating %s resource: %s, cleanup source: %s",
            resource_type,
            resource_id,
            cleanup_source,
        )
        if include_dependencies:
            associated_resources = self._get_associated_resources(
                resource_type, resource_id
            )
            for resource in associated_resources["pending"]:
                LOG.info(
                    "DRY-RUN: migrating associated %s resource: %s.",
                    resource.resource_type,
                    resource.source_id,
                )
                self._perform_individual_migration_dry_run(
                    resource.resource_type,
                    resource.source_id,
                    cleanup_source=cleanup_source,
                    include_dependencies=include_dependencies,
                    include_members=include_members,
                )
            for resource in associated_resources["migrated"]:
                LOG.info(
                    "DRY-RUN: already migrated associated %s resource: %s -> %s",
                    resource.resource_type,
                    resource.source_id,
                    resource.destination_id,  # type: ignore [attr-defined]
                )
        if include_members:
            member_resources = handler.get_member_resources(resource_id)
            for resource in member_resources:
                LOG.info(
                    "DRY-RUN: migrating member %s resource: %s.",
                    resource.resource_type,
                    resource.source_id,
                )
                self._perform_individual_migration_dry_run(
                    resource_type,
                    resource_id,
                    cleanup_source=cleanup_source,
                    include_dependencies=include_dependencies,
                    include_members=include_members,
                )

        # Return an empty migration.
        return models.Migration()
