# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
import os
import random
import subprocess
from pathlib import Path

import openstack

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
        session = openstack.connect(cloud=cloud_name)
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
