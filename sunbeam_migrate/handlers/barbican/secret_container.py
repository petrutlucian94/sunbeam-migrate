# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate import config, exception
from sunbeam_migrate.handlers import base
from sunbeam_migrate.utils import barbican_utils

CONF = config.get_config()


class SecretContainerHandler(base.BaseMigrationHandler):
    """Handle Barbican secret container migrations."""

    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        return "barbican"

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types."""
        return ["secret"]

    def get_associated_resources(self, resource_id: str) -> list[base.Resource]:
        """Get a list of associated resources."""
        container_id = barbican_utils.parse_barbican_url(resource_id)
        container = self._source_session.key_manager.get_container(container_id)
        if not (container and container.id):
            raise exception.NotFound(f"Secret not found: {resource_id}")

        associated_resources = []
        for secret_ref_dict in container.secret_refs:
            associated_resources.append(
                base.Resource(
                    resource_type="secret",
                    source_id=secret_ref_dict["secret_ref"],
                    should_cleanup=True,
                )
            )

        return associated_resources

    def perform_individual_migration(
        self,
        resource_id: str,
        migrated_associated_resources: list[base.MigratedResource],
    ) -> str:
        """Migrate the specified resource.

        :param resource_id: the resource to be migrated
        :param migrated_associated_resources: a list of MigratedResource
               objects describing migrated dependencies.

        Return the resulting resource id.
        """
        source_container_id = barbican_utils.parse_barbican_url(resource_id)
        source_container = self._source_session.key_manager.get_container(
            source_container_id
        )
        if not source_container:
            raise exception.NotFound(f"Secret not found: {resource_id}")

        # TODO: pass the project name if needed.
        fields = ["name", "type"]
        kwargs = {}
        for field in fields:
            value = getattr(source_container, field, None)
            if value:
                kwargs[field] = value

        secret_refs = []
        for secret_ref_dict in source_container.secret_refs:
            destination_ref = self._get_associated_resource_destination_id(
                "secret", secret_ref_dict["secret_ref"], migrated_associated_resources
            )
            secret_refs.append(
                {
                    "name": secret_ref_dict["name"],
                    "secret_ref": destination_ref,
                }
            )
        kwargs["secret_refs"] = secret_refs

        destination_secret = self._destination_session.key_manager.create_container(
            **kwargs
        )

        return destination_secret.id

    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        self._validate_resource_filters(resource_filters)

        query_filters = {}
        if "owner_id" in resource_filters:
            query_filters["owner"] = resource_filters["owner_id"]

        resource_ids = []
        for resource in self._source_session.key_manager.containers(**query_filters):
            resource_ids.append(resource.id)

        return resource_ids

    def _delete_resource(self, resource_id: str, openstack_session):
        container_id = barbican_utils.parse_barbican_url(resource_id)
        openstack_session.key_manager.delete_container(container_id)
