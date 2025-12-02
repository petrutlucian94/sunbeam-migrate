# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import json

import click
import prettytable

from sunbeam_migrate.db import api, models


@click.command("show")
@click.argument("migration_id")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Set the output format.",
)
def show_migration(output_format: str, migration_id: str):
    """Show migration information."""
    if not migration_id:
        raise click.ClickException("No migration id specified.")

    migrations = api.get_migrations(uuid=migration_id, include_archived=True)
    if not migrations:
        raise click.ClickException(
            f"Could not find the specified migration: {migration_id}"
        )
    if len(migrations) > 1:
        raise click.ClickException(f"Multiple migrations found: {migration_id}")

    if output_format == "table":
        _table_format(migrations[0])
    else:
        _json_format(migrations[0])


def _table_format(migration: models.Migration):
    table = prettytable.PrettyTable()
    table.title = "Migration"
    table.field_names = ["Field", "Value"]
    fields = [
        "uuid",
        "created_at",
        "updated_at",
        "service",
        "resource_type",
        "source_cloud",
        "destination_cloud",
        "source_id",
        "destination_id",
        "status",
        "error_message",
        "archived",
        "source_removed",
        "external",
    ]

    for field in fields:
        value = getattr(migration, field)
        table_field_name = field.replace("_", " ").capitalize()
        table.add_row([table_field_name, value])
    print(table)


def _json_format(migration: models.Migration):
    print(json.dumps(migration.to_dict()))
