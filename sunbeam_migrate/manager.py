# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from sunbeam_migrate import config, constants, exception
from sunbeam_migrate.db import api as db_api
from sunbeam_migrate.db import models
from sunbeam_migrate.handlers import factory

CONFIG = config.get_config()
LOG = logging.getLogger()


class SunbeamMigrationManager:
    def perform_individual_migration(
        self,
        resource_type: str,
        resource_id: str,
        cleanup_source: bool = False,
        include_dependencies: bool = False,
    ) -> models.Migration:
        """Migrate the specified resource."""
        handler = factory.get_migration_handler(resource_type)

        if not resource_id:
            raise exception.InvalidInput("No resource id specified.")

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

        try:
            associated_migrations = []
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
                    LOG.info(
                        "Migrating associated %s resource: %s",
                        assoc_resource_type,
                        assoc_resource_id,
                    )
                    associated_migration = self.perform_individual_migration(
                        assoc_resource_type,
                        assoc_resource_id,
                        include_dependencies=include_dependencies,
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
        except Exception as ex:
            migration.status = constants.STATUS_FAILED
            migration.error_message = "Migration failed, error: %r" % ex
            migration.save()
            raise

        if cleanup_source:
            self.cleanup_migration_source(migration)

            for associated_migration in associated_migrations:
                self.cleanup_migration_source(associated_migration)

        LOG.info("Successfully migrated resource, destination id: %s", destination_id)
        migration.status = constants.STATUS_COMPLETED
        migration.destination_id = destination_id
        migration.save()
        return migration

    def _get_associated_resources(
        self,
        resource_type: str,
        resource_id: str,
    ) -> dict[str, list[tuple]]:
        handler = factory.get_migration_handler(resource_type)
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
    ):
        """Migrate multiple resources that match the specified filters."""
        handler = factory.get_migration_handler(resource_type)

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
            handler = factory.get_migration_handler(migration.resource_type)
            handler.delete_source_resource(migration.source_id)
            migration.source_removed = True
            migration.save()
        except Exception as ex:
            migration.status = constants.STATUS_SOURCE_CLEANUP_FAILED
            migration.error_message = "Source cleanup failed, error: %r" % ex
            migration.save()
            raise
