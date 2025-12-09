# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate import exception
from sunbeam_migrate.handlers import base


class PortHandler(base.BaseMigrationHandler):
    """Handle Neutron port migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "neutron"

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return []

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types.

        Ports depend on networks, subnets, and security groups,
        which must be migrated first.
        """
        return ["network", "subnet", "security-group"]

    def get_associated_resources(self, resource_id: str) -> list[tuple[str, str]]:
        """Return the source resources this port depends on."""
        source_port = self._source_session.network.get_port(resource_id)
        if not source_port:
            raise exception.NotFound(f"Port not found: {resource_id}")

        associated_resources = []
        if source_port.network_id:
            associated_resources.append(("network", source_port.network_id))

        # Add subnets as associated resources from fixed_ips
        fixed_ips = source_port.fixed_ips or []
        for fixed_ip in fixed_ips:
            subnet_id = fixed_ip.get("subnet_id")
            if subnet_id:
                associated_resources.append(("subnet", subnet_id))

        # Add security groups as associated resources
        security_group_ids = source_port.security_group_ids or []
        for sg_id in security_group_ids:
            associated_resources.append(("security-group", sg_id))

        return associated_resources

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
        source_port = self._source_session.network.get_port(resource_id)
        if not source_port:
            raise exception.NotFound(f"Port not found: {resource_id}")

        destination_network_id = self._get_associated_resource_destination_id(
            "network",
            source_port.network_id,
            migrated_associated_resources,
        )

        fields = [
            "admin_state_up",
            "allowed_address_pairs",
            # "binding_host_id",
            "binding_profile",
            # "binding_vif_details",
            # "binding_vif_type",
            "binding_vnic_type",
            # "data_plane_status",
            "description",
            # "device_id",
            # "device_owner",
            # "dns_assignment",
            "dns_name",
            "extra_dhcp_opts",
            # "fixed_ips",  # Handled explicitly with subnet ID mapping
            "mac_address",
            "name",
            "port_security_enabled",
            "qos_policy_id",
            # "resource_request",
            "tags",
            # "trunk_details",
        ]
        kwargs = {}
        for field in fields:
            value = getattr(source_port, field, None)
            if value is not None:
                kwargs[field] = value

        # Map security group IDs from source to destination
        destination_security_group_ids = []
        for sg_id in source_port.security_group_ids:
            dest_sg_id = self._get_associated_resource_destination_id(
                "security-group",
                sg_id,
                migrated_associated_resources,
            )
            destination_security_group_ids.append(dest_sg_id)

        # Map subnet IDs in fixed_ips from source to destination
        fixed_ips = source_port.fixed_ips or []
        destination_fixed_ips = []
        for fixed_ip in fixed_ips:
            dest_fixed_ip = fixed_ip.copy()
            if "subnet_id" in dest_fixed_ip and dest_fixed_ip["subnet_id"]:
                dest_subnet_id = self._get_associated_resource_destination_id(
                    "subnet",
                    dest_fixed_ip["subnet_id"],
                    migrated_associated_resources,
                )
                dest_fixed_ip["subnet_id"] = dest_subnet_id
            destination_fixed_ips.append(dest_fixed_ip)

        kwargs["network_id"] = destination_network_id
        if destination_security_group_ids:
            kwargs["security_group_ids"] = destination_security_group_ids
        if destination_fixed_ips:
            kwargs["fixed_ips"] = destination_fixed_ips

        destination_port = self._destination_session.network.create_port(**kwargs)
        return destination_port.id

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        # Batch port migration doesn't make much sense. Ports will most often be
        # migrated as Nova instance dependencies.
        raise exception.NotSupported("Batch port migration is unsupported.")

    def _delete_resource(self, resource_id: str, openstack_session):
        openstack_session.network.delete_port(resource_id, ignore_missing=True)
