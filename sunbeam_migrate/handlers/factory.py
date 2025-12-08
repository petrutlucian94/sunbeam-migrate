# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import importlib

from sunbeam_migrate import exception
from sunbeam_migrate.handlers import base

MIGRATION_HANDLERS = {
    # Barbican handlers
    "secret": "sunbeam_migrate.handlers.barbican.secret.SecretHandler",
    "secret-container": "sunbeam_migrate.handlers.barbican.secret_container.SecretContainerHandler",
    # Cinder handles
    "volume": "sunbeam_migrate.handlers.cinder.volume.VolumeHandler",
    "volume-type": "sunbeam_migrate.handlers.cinder.volume_type.VolumeTypeHandler",
    # Glance handlers
    "image": "sunbeam_migrate.handlers.glance.image.ImageHandler",
    # Keystone handlers
    "domain": "sunbeam_migrate.handlers.keystone.domain.DomainHandler",
    "project": "sunbeam_migrate.handlers.keystone.project.ProjectHandler",
    "user": "sunbeam_migrate.handlers.keystone.user.UserHandler",
    # Manila handlers
    "share": "sunbeam_migrate.handlers.manila.share.ShareHandler",
    "share-type": "sunbeam_migrate.handlers.manila.share_type.ShareTypeHandler",
    # Nova handlers
    "flavor": "sunbeam_migrate.handlers.nova.flavor.FlavorHandler",
    # Neutron handlers
    "router": "sunbeam_migrate.handlers.neutron.router.RouterHandler",
    "network": "sunbeam_migrate.handlers.neutron.network.NetworkHandler",
    "subnet": "sunbeam_migrate.handlers.neutron.subnet.SubnetHandler",
    "security-group": "sunbeam_migrate.handlers.neutron.security_group.SecurityGroupHandler",
    "security-group-rule": "sunbeam_migrate.handlers.neutron.security_group_rule.SecurityGroupRuleHandler",
}


def get_migration_handler(resource_type: str | None) -> base.BaseMigrationHandler:
    """Get the migration handler for the given resource type."""
    if not resource_type:
        raise exception.InvalidInput("No resource type specified.")
    if resource_type not in MIGRATION_HANDLERS:
        raise exception.InvalidInput("Unsupported resource type: %s" % resource_type)

    module_name, class_name = MIGRATION_HANDLERS[resource_type].rsplit(".", 1)
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls()


def get_all_handlers() -> dict[str, base.BaseMigrationHandler]:
    """Get instances of all the supported resource handlers."""
    handlers: dict[str, base.BaseMigrationHandler] = {}
    for resource_type in MIGRATION_HANDLERS:
        handlers[resource_type] = get_migration_handler(resource_type)
    return handlers
