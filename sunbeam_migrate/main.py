# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
import sys
from pathlib import Path

import click

from sunbeam_migrate import config, log
from sunbeam_migrate.cmd import capabilities as capabilities_cmd
from sunbeam_migrate.cmd import cleanup_source as cleanup_source_cmd
from sunbeam_migrate.cmd import delete as delete_cmd
from sunbeam_migrate.cmd import list as list_cmd
from sunbeam_migrate.cmd import register_external as register_external_cmd
from sunbeam_migrate.cmd import restore as restore_cmd
from sunbeam_migrate.cmd import show as show_cmd
from sunbeam_migrate.cmd import start as start_cmd
from sunbeam_migrate.db import api as db_api

LOG = logging.getLogger()

# Update the help options to allow -h in addition to --help for
# triggering the help for various commands
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group("init", context_settings=CONTEXT_SETTINGS)
@click.option("--config", "-c", "config_path", envvar="SUNBEAM_MIGRATE_CONFIG")
@click.option("--debug", is_flag=True, help="Debug logging.")
@click.pass_context
def cli(ctx, config_path: str, debug: bool):
    """Migrate resources between Openstack clouds.

    This tool is primarily designed to assist the migration from
    Charmed Openstack to Canonical Openstack (Sunbeam).
    """
    if config_path:
        config.load_config(Path(config_path))

    log.configure_logging(debug=debug)
    db_api.initialize()
    db_api.create_tables()

    if config_path:
        LOG.debug("Loaded config: %s", config_path)


def main():
    """Main entry point."""
    LOG.debug("command: %s", " ".join(sys.argv))

    cli.add_command(capabilities_cmd.show_capabilities)
    cli.add_command(list_cmd.list_migrations)
    cli.add_command(show_cmd.show_migration)
    cli.add_command(start_cmd.start_migration)
    cli.add_command(start_cmd.start_batch_migration)
    cli.add_command(delete_cmd.delete_migrations)
    cli.add_command(restore_cmd.restore_migrations)
    cli.add_command(cleanup_source_cmd.cleanup_migration_sources)
    cli.add_command(register_external_cmd.register_external)

    cli()


if __name__ == "__main__":
    main()
