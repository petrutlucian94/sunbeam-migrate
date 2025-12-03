# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import os
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel


class LogLevel(str, Enum):
    """Python log level."""

    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"


class SunbeamMigrateConfig(BaseModel):
    """sunbeam-migrate coniguration."""

    log_level: LogLevel = LogLevel.info
    log_dir: Path | None = None
    # Whether to use console logging.
    log_console: bool = True
    # The Openstack cloud config file to use, expected to contain
    # credentials for both the source and the destination clouds.
    # https://docs.openstack.org/openstacksdk/latest/user/config/configuration.html
    cloud_config_file: Path | None = None
    source_cloud_name: str | None = None
    destination_cloud_name: str | None = None
    database_file: Path = Path(
        os.path.expandvars("$HOME/.local/share/sunbeam-migrate/sqlite.db")
    )
    image_transfer_chunk_size: int = 32 * 1024 * 1024  # 32MB
    # Preserve the volume type when migrating volumes. Defaults to "false" for
    # increased compatibility. If enabled, the volume types will be migrated and
    # used when transferring volumes. Manually created types may be registered
    # using the "register-external" command.
    preserve_volume_type: bool | None = False
    # Preserve the volume availability zone when migrating volumes.
    # Defaults to "false" for increased compatibility.
    preserve_volume_availability_zone: bool | None = False
    volume_upload_timeout: int = 1800

    def load_config(self, path: Path):
        """Load the configuration from the specified file."""
        with path.open() as f:
            cfg_yaml = yaml.safe_load(f)

            updated = self.model_validate({**self.model_dump(), **cfg_yaml})
            self.__dict__.update(updated.__dict__)


_CONFIG: SunbeamMigrateConfig | None = None


def get_config() -> SunbeamMigrateConfig:
    """Retrieve the global config object."""
    global _CONFIG
    if not _CONFIG:
        _CONFIG = SunbeamMigrateConfig()
    return _CONFIG


def load_config(path: Path):
    """Load the configuration from the specified file."""
    get_config().load_config(path)
