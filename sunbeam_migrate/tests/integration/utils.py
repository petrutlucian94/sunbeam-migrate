# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
import random
import subprocess
from pathlib import Path

import openstack

from sunbeam_migrate import constants

LOG = logging.getLogger()


def get_openstack_session(cloud_config_path: Path, cloud_name: str):
    if not cloud_config_path:
        raise ValueError("No cloud config provided.")
    if not cloud_name:
        raise ValueError("No cloud name specified.")

    previous_env_var = os.environ.get("OS_CLIENT_CONFIG_FILE")
    os.environ["OS_CLIENT_CONFIG_FILE"] = str(cloud_config_path)
    try:
        LOG.info(
            "Connecting to %s cloud. Config: %s.", cloud_name, str(cloud_config_path)
        )
        session = openstack.connect(
            cloud=cloud_name,
            share_api_version=constants.MANILA_MICROVERSION,
        )
    finally:
        if previous_env_var:
            os.environ["OS_CLIENT_CONFIG_FILE"] = previous_env_var

    return session


def get_test_resource_name() -> str:
    return "test-%s" % random.randint(0, 1 << 32)


def call_migrate(config_path: Path, command: list[str]):
    command = ["sunbeam-migrate", "--config", str(config_path)] + command
    subprocess.check_call(command, text=True)


def check_migrate(config_path: Path, command: list[str]) -> str:
    """Run the sunbeam-migrate command and capture the output."""
    command = ["sunbeam-migrate", "--config", str(config_path)] + command
    return subprocess.check_output(command, text=True)


def get_migrations(
    config_path: Path,
    resource_type: str | None = None,
    source_id: str | None = None,
) -> list[dict]:
    # We avoid using the db directly, exercising the commands instead.
    command = ["list", "-f", "json"]
    if source_id:
        command += ["--source-id", source_id]
    if resource_type:
        command += ["--resource-type", resource_type]

    migrations_json = check_migrate(config_path, command) or "[]"
    return json.loads(migrations_json) or []


def get_destination_resource_id(
    config_path: Path,
    resource_type: str,
    source_id: str,
) -> str:
    migrations = get_migrations(config_path, resource_type, source_id)
    if not migrations:
        raise ValueError(
            "Migrated {resource_type} not found, source resource: {source_id}."
        )
    return migrations[-1]["destination_id"]
