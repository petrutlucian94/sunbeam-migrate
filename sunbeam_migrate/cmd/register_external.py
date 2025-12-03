# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

import click

from sunbeam_migrate import config, constants
from sunbeam_migrate.db import api as db_api
from sunbeam_migrate.db import models
from sunbeam_migrate.handlers import factory

CONFIG = config.get_config()
LOG = logging.getLogger()


@click.command("register-external")
@click.option("--resource-type", help="The migrated resource type (e.g. image, secret)")
@click.argument("source_resource_id")
@click.argument("destination_resource_id")
def register_external(
    resource_type: str,
    source_resource_id: str,
    destination_resource_id: str,
):
    """Register an external migration.

    This command can be used to declare a migration that was performed externally
    so that sunbeam-migrate will not attempt the migration again. Dependent resources
    will automatically use the specified resource.

    Let's take volume types for example. The extra specs may contain backend specific
    properties that are not applicable on the destination cloud (e.g. backend name,
    pool name or other storage backend settings). "sunbeam-migrate" would make an
    exact copy of the source type, which may not be desired.

    Instead, the user can recreate the volume type manually on the destination cloud
    and then use this command to register the migration. Subsequent volume migrations
    will automatically use the manually created volume type.
    """
    if not source_resource_id:
        raise click.ClickException("Unspecified source resource id.")
    if not destination_resource_id:
        raise click.ClickException("Unspecified destination resource id.")
    if not resource_type:
        raise click.ClickException("Unspecified resource type.")

    migrations = db_api.get_migrations(
        resource_type=resource_type,
        source_id=source_resource_id,
        destination_id=destination_resource_id,
        status=constants.STATUS_COMPLETED,
    )
    if migrations:
        LOG.warning("Found existing migration: %s, skipping...", migrations[0].uuid)
        return

    handler = factory.get_migration_handler(resource_type)
    migration = models.Migration(
        service=handler.get_service_type(),
        source_cloud=CONFIG.source_cloud_name,
        destination_cloud=CONFIG.destination_cloud_name,
        source_id=source_resource_id,
        resource_type=resource_type,
        destination_id=destination_resource_id,
        status=constants.STATUS_COMPLETED,
        external=True,
    )
    migration.save()
