# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import typing

import click
import prettytable

from sunbeam_migrate.handlers import factory


@click.command("capabilities")
@click.option(
    "--resource-type", help="Migration capabilities for a given resource type."
)
def show_capabilities(resource_type: str):
    """Describe migration capabilities."""
    if not resource_type:
        _show_all_migration_handlers()
    else:
        _show_migration_handler(resource_type)


def _user_friendly_list(input_list: list[typing.Any]):
    return ", ".join(str(item) for item in input_list) or "-"


def _show_all_migration_handlers():
    table = prettytable.PrettyTable()
    table.title = "Migration handlers"
    table.field_names = [
        "Service",
        "Resource type",
        "Member resource types",
        "Associated resource types",
        "Batch resource filters",
    ]
    table.sortby = "Service"
    for resource_type, handler in factory.get_all_handlers().items():
        table.add_row(
            [
                handler.get_service_type().capitalize(),
                resource_type,
                _user_friendly_list(handler.get_member_resource_types()),
                _user_friendly_list(handler.get_associated_resource_types()),
                _user_friendly_list(handler.get_supported_resource_filters()),
            ]
        )
    print(table)


def _show_migration_handler(resource_type: str):
    table = prettytable.PrettyTable()
    table.title = "Migration handler"
    table.field_names = ["Property", "Value"]
    handler = factory.get_migration_handler(resource_type)
    table.add_row(["Service", handler.get_service_type().capitalize()])
    table.add_row(["Resource type", resource_type])
    table.add_row(
        [
            "Member resource types",
            _user_friendly_list(handler.get_member_resource_types()),
        ]
    )
    table.add_row(
        [
            "Associated resource types",
            _user_friendly_list(handler.get_associated_resource_types()),
        ]
    )
    table.add_row(
        [
            "Batch resource filters",
            _user_friendly_list(handler.get_supported_resource_filters()),
        ]
    )
    print(table)
