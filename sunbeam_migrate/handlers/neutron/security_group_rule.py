# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
import re

from openstack import exceptions as openstack_exc

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base

CONF = config.get_config()
LOG = logging.getLogger(__name__)


class SecurityGroupRuleHandler(base.BaseMigrationHandler):
    """Handle Barbican secret container migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "neutron"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return ["owner_id"]

    def get_associated_resource_types(self) -> list[str]:
        """Security group rules depend on their security group."""
        return ["security-group"]

    def get_associated_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Return the security groups referenced by this rule."""
        source_rule = self._source_session.network.get_security_group_rule(resource_id)
        if not source_rule:
            raise exception.NotFound(f"Security Group Rule not found: {resource_id}")
        resources = [("security-group", source_rule.security_group_id)]
        if source_rule.remote_group_id:
            resources.append(("security-group", source_rule.remote_group_id))
        return resources

    def get_member_resource_types(self) -> list[str]:
        """Get a list of member (contained) resource types.

        The migrations can cascade to contained resources.
        """
        return []

    def perform_individual_migration(
        self,
        resource_id: str,
        migrated_associated_resources: list[tuple[str, str, str]],
    ) -> str:
        """Migrate the specified resource.

        :param resource_id: the resource to be migrated
        :param migrated_associated_resources: a list of tuples describing
            associated resources that have already been migrated.
            Format: (resource_type, source_id, destination_id)

        Return the resulting resource id.
        """
        source_sg_rule = self._source_session.network.get_security_group_rule(
            resource_id
        )
        if not source_sg_rule:
            raise exception.NotFound(f"Security Group Rule not found: {resource_id}")

        dest_security_group_id = self._get_associated_resource_destination_id(
            "security-group",
            source_sg_rule.security_group_id,
            migrated_associated_resources,
        )

        fields = [
            "description",
            "direction",
            "ether_type",
            "port_range_min",
            "port_range_max",
            "protocol",
            "remote_ip_prefix",
        ]
        kwargs = {}
        for field in fields:
            value = getattr(source_sg_rule, field, None)
            if value is not None:
                kwargs[field] = value

        # Handle remote_group_id (needs resolution)
        if source_sg_rule.remote_group_id:
            kwargs["remote_group_id"] = self._get_associated_resource_destination_id(
                "security-group",
                source_sg_rule.remote_group_id,
                migrated_associated_resources,
            )

        try:
            destination_sg_rule = (
                self._destination_session.network.create_security_group_rule(
                    security_group_id=dest_security_group_id,
                    **kwargs,
                )
            )
            return destination_sg_rule.id
        except openstack_exc.ConflictException as exc:
            # Rule id appears in the exception message if it already exists
            existing_rule_id = ""
            details = str(exc)

            match = re.search(
                r"Rule id is ([0-9a-fA-F-]{36})",
                details,
            )
            if match:
                existing_rule_id = match.group(1)

            if existing_rule_id:
                LOG.info(
                    "Security group rule already exists on destination SG %s, "
                    "reusing rule %s",
                    dest_security_group_id,
                    existing_rule_id,
                )
                return existing_rule_id
            raise exc

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "owner_id" in resource_filters:
            query_filters["project_id"] = resource_filters["owner_id"]

        resource_ids = []
        for sg_rule in self._source_session.network.security_group_rules(
            **query_filters
        ):
            resource_ids.append(sg_rule.id)

        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.network.delete_security_group_rule(
            resource_id, ignore_missing=True
        )
