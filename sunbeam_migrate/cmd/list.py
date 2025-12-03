# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import json
import typing

import click
import prettytable

from sunbeam_migrate.db import api, models


@click.command("list")
@click.option("--service", help="Filter by service name")
@click.option("--resource-type", help="Filter by resource type")
@click.option("--status", help="Filter by migration status.")
@click.option("--source-id", help="Filter by source resource id.")
@click.option("--archived", is_flag=True, help="Only show archived migrations.")
@click.option("--include-archived", is_flag=True, help="Include archived migrations.")
@click.option("--external", is_flag=True, help="Only show external migrations.")
@click.option(
    "--source-removed",
    is_flag=True,
    help="Only show resources cleaned up from the source.",
)
@click.option(
    "--exclude-source-removed",
    is_flag=True,
    help="Exclude resources cleaned up from the source.",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "table"]),
    default="table",
    help="Set the output format.",
)
def list_migrations(
    output_format: str,
    service: str,
    resource_type: str,
    status: str,
    source_id: str,
    archived: bool,
    include_archived: bool,
    external: bool,
    source_removed: bool,
    exclude_source_removed: bool,
):
    """List migrations."""
    filters: dict[str, typing.Any] = {}
    if service:
        filters["service"] = service
    if resource_type:
        filters["resource_type"] = resource_type
    if status:
        filters["status"] = status
    if source_id:
        filters["source_id"] = source_id
    if archived:
        filters["archived"] = True
    if external:
        filters["external"] = True

    if source_removed and exclude_source_removed:
        raise click.ClickException(
            "Both --source-removed and --exclude-source-removed flags were specified."
        )
    if source_removed:
        filters["source_removed"] = True
    elif exclude_source_removed:
        filters["source_removed"] = False

    migrations = api.get_migrations(include_archived=include_archived, **filters)

    if output_format == "table":
        _table_format(migrations)
    else:
        _json_format(migrations)


def _table_format(migrations: list[models.Migration]):
    table = prettytable.PrettyTable()
    table.title = "Migrations"
    table.field_names = [
        "UUID",
        "Service",
        "Resource type",
        "Status",
        "Source ID",
        "Destination ID",
    ]
    for entry in migrations:
        if entry.service == "barbican":
            # Show just the ids instead of the full resource URLs
            # in order to maintain readability. The full URLs can be obtained
            # using the "show" command.
            entry.source_id = (entry.source_id or "").split("/")[-1]
            entry.destination_id = (entry.destination_id or "").split("/")[-1]
        table.add_row(
            [
                entry.uuid,
                entry.service,
                entry.resource_type,
                entry.status,
                entry.source_id,
                entry.destination_id,
            ]
        )
    print(table)


def _json_format(migrations: list[models.Migration]):
    migration_dict_list = [migration.to_dict() for migration in migrations]
    print(json.dumps(migration_dict_list))
