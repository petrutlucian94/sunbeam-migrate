# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

import click

from sunbeam_migrate import manager

LOG = logging.getLogger()


@click.command("start")
@click.option("--resource-type", help="The migrated resource type (e.g. image, secret)")
@click.argument("resource_id")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Only log the steps to be executed, skipping migrations.",
)
@click.option(
    "--cleanup-source",
    is_flag=True,
    help="Cleanup the resources on the source side if the migration succeeds.",
)
@click.option(
    "--include-dependencies",
    is_flag=True,
    help="Automatically migrate associated resources.",
)
@click.option(
    "--include-members",
    is_flag=True,
    help="Automatically migrate member resources (contained resources).",
)
def start_migration(
    resource_type: str,
    resource_id: str,
    dry_run: bool,
    cleanup_source: bool,
    include_dependencies: bool,
    include_members: bool,
):
    """Migrate an individual resource."""
    mgr = manager.SunbeamMigrationManager()
    mgr.perform_individual_migration(
        resource_type,
        resource_id,
        dry_run=dry_run,
        cleanup_source=cleanup_source,
        include_dependencies=include_dependencies,
        include_members=include_members,
    )


@click.command("start-batch")
@click.option("--resource-type", help="The migrated resource type (e.g. image, secret)")
@click.option(
    "--filter",
    "resource_filters",
    multiple=True,
    help="One or more filters used to select the resources to migrate.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Only log the steps to be executed, skipping migrations.",
)
@click.option("--all", "migrate_all", is_flag=True, help="Migrate all resources.")
@click.option(
    "--cleanup-source",
    is_flag=True,
    help="Cleanup the resources on the source side if the migration succeeds.",
)
@click.option(
    "--include-dependencies",
    is_flag=True,
    help="Automatically migrate associated resources.",
)
@click.option(
    "--include-members",
    is_flag=True,
    help="Automatically migrate member resources (contained resources).",
)
def start_batch_migration(
    resource_type: str,
    resource_filters: tuple[str],
    dry_run: bool,
    migrate_all: bool,
    cleanup_source: bool,
    include_dependencies: bool,
    include_members: bool,
):
    """Migrate multiple resources that match the filters."""
    if not resource_type:
        raise click.ClickException("No resource type specified.")
    if not resource_filters and not migrate_all:
        raise click.ClickException(
            "No filters specified. Specify '--all' to migrate all resources."
        )

    resource_filters_dict: dict[str, str] = {}
    for str_filter in resource_filters or []:
        if ":" not in str_filter:
            raise click.ClickException(
                "Invalid resource filter, "
                f"expecting 'key:value' arguments: {str_filter}"
            )
        key, val = str_filter.split(":", 1)
        resource_filters_dict[key.replace("-", "_")] = val

    mgr = manager.SunbeamMigrationManager()
    mgr.perform_batch_migration(
        resource_type,
        resource_filters_dict,
        dry_run=dry_run,
        cleanup_source=cleanup_source,
        include_dependencies=include_dependencies,
        include_members=include_members,
    )
