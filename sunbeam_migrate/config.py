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
    # The directory used to store temporary files and mounts
    # used as part of the migration process.
    temporary_migration_dir: Path = Path(
        os.path.expandvars("$HOME/.local/share/sunbeam-migrate/migration_dir")
    )
    # The multitenant mode allows identifying and migrating resources owned by
    # another tenant. This requires admin privileges.
    # The identity resources (domain, project, user) will be treated as
    # dependencies and migrated automatically if "--include-dependencies" is set.
    multitenant_mode: bool = True

    image_transfer_chunk_size: int = 32 * 1024 * 1024  # 32MB

    volume_upload_timeout: int = 1800
    # How much to wait for OpenStack resource provisioning.
    resource_creation_timeout: int = 300

    # Preserve the volume type when migrating volumes. Defaults to "false" for
    # increased compatibility. If enabled, the volume types will be migrated and
    # used when transferring volumes. Manually created types may be registered
    # using the "register-external" command.
    preserve_volume_type: bool = False
    # Preserve the volume availability zone when migrating volumes.
    # Defaults to "false" for increased compatibility.
    preserve_volume_availability_zone: bool = False
    preserve_instance_availability_zone: bool = False
    preserve_load_balancer_availability_zone: bool = False
    # Preserve the Manila share type.
    preserve_share_type: bool = False
    # Preserve the network segmentation ID (e.g. VLAN tag or tunnel VNI).
    # This is disabled by default since it may conflict with other existing
    # networks from the destination cloud.
    preserve_network_segmentation_id: bool = False
    preserve_port_mac_address: bool = False
    # Whether to recreate floating IPs attached to migrated ports.
    preserve_port_floating_ip: bool = False
    # Whether the use the same IP address when moving floating IPs.
    preserve_port_floating_ip_address: bool = True
    # Whether to preserve the port fixed IPs.
    preserve_port_fixed_ips: bool = True
    preserve_router_ip: bool = True

    # The local IP used to access Manila shares. A temporary share access
    # rule will be defined, ensuring that the local host can access the
    # share that's being migrated. If not provided, it will be detected
    # automatically.
    manila_local_access_ip: str | None = None

    # The name of the "member" Keystone role. When migrating certain resources
    # to other tenants (e.g. instances, volumes, shares), we need to a project
    # scoped session using the destination project.
    #
    # sunbeam-migrate will transparently assign the member role to the user
    # that initiated the migration.
    member_role_name: str = "member"

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
