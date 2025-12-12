# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import abc
import logging
import os

import openstack
import pydantic

from sunbeam_migrate import config, constants, exception

CONF = config.get_config()
LOG = logging.getLogger()


class Resource(pydantic.BaseModel):
    """Resource class.

    Migration handlers use this class to describe resource dependencies.
    The migration manager will ensure that the requested resources are
    migrated before initiating the dependent resource migration.
    """

    resource_type: str
    source_id: str
    # Whether the specified resource should be cleaned up.
    # Shared resources (e.g. networks, flavor) should not be removed when
    # one of the dependent resources are migrated (e.g. port, instance).
    should_cleanup: bool = False


class MigratedResource(Resource):
    """Migrated resource class.

    Migration handlers receive information about migrated dependencies
    using this class.
    """

    destination_id: str


class BaseMigrationHandler(abc.ABC):
    """Base migration class."""

    def __init__(self, *args, **kwargs):
        self._manager = None

    @abc.abstractmethod
    def get_service_type(self) -> str:
        """Get the service type for this type of resource."""
        pass

    @abc.abstractmethod
    def perform_individual_migration(
        self,
        resource_id: str,
        migrated_associated_resources: list[MigratedResource],
    ) -> str:
        """Migrate the specified resource.

        :param resource_id: the resource to be migrated
        :param migrated_associated_resources: a list of MigratedResource
               objects describing migrated dependencies.

        Return the resulting resource id.
        """
        pass

    @abc.abstractmethod
    def get_source_resource_ids(self, resource_filters: dict[str, str]) -> list[str]:
        """Returns a list of resource ids based on the specified filters.

        Raises an exception if any of the filters are unsupported.
        """
        pass

    def delete_source_resource(self, resource_id: str):
        """Delete the specified resource on the source cloud side."""
        self._delete_resource(resource_id, self._source_session)

    def delete_destination_resource(self, resource_id: str):
        """Delete the specified resource on the destination cloud side."""
        self._delete_resource(resource_id, self._destination_session)

    def _delete_resource(self, resource_id: str, openstack_session):
        raise NotImplementedError()

    def get_member_resource_types(self) -> list[str]:
        """Get a list of member (contained) resource types.

        The migrations can cascade to contained resources.

        Examples:
        * network -> subnet
        * security group -> security group rule
        * object-container -> object
        """
        return []

    def get_member_resources(self, resource_id: str) -> list[Resource]:
        """Get a list of member resources.

        We're using a list instead of a dict so that the handler can control
        the order in which associated resources are migrated.
        """
        return []

    def get_associated_resource_types(self) -> list[str]:
        """Get a list of associated resource types.

        Associated resources must be migrated first.

        Examples:
        * secret-container -> secret,
        * instance -> volume
        * instance -> port
        """
        return []

    def get_associated_resources(self, resource_id: str) -> list[Resource]:
        """Get a list of associated resources.

        We're using a list instead of a dict so that the handler can control
        the order in which dependent resources are migrated.
        """
        return []

    def get_supported_resource_filters(self) -> list[str]:
        """Get a list of supported resource filters.

        These filters can be specified when initiating batch migrations.
        """
        return []

    def connect_member_resources_to_parent(
        self,
        parent_resource_id: str | None,
        migrated_member_resources: list[MigratedResource],
    ):
        """Connect member resources to the parent resource.

        This is called after member resources have been migrated.

        :param parent_resource_id: The destination ID of the parent resource,
                                   having the same type as that of the handler.
        :param migrated_member_resources: a list of MigratedResource
               objects describing migrated member resources.
        """
        pass

    def _get_openstack_session(self, cloud_name: str):
        if not CONF.cloud_config_file:
            raise exception.InvalidInput("No cloud config provided.")

        os.environ["OS_CLIENT_CONFIG_FILE"] = str(CONF.cloud_config_file)
        return openstack.connect(
            cloud=cloud_name,
            compute_api_version=constants.NOVA_MICROVERSION,
            share_api_version=constants.MANILA_MICROVERSION,
        )

    @property
    def _source_session(self):
        if not CONF.source_cloud_name:
            raise exception.InvalidInput("No source cloud specified.")

        if not getattr(self, "_cached_source_session", None):
            self._cached_source_session = self._get_openstack_session(
                CONF.source_cloud_name
            )

        return self._cached_source_session

    @property
    def _destination_session(self):
        if not CONF.destination_cloud_name:
            raise exception.InvalidInput("No destination cloud specified.")

        if not getattr(self, "_cached_destinaton_session", None):
            self._cached_destinaton_session = self._get_openstack_session(
                CONF.destination_cloud_name
            )

        return self._cached_destinaton_session

    def _report_identity_dependencies(
        self,
        associated_resources: list[Resource],
        project_id: str | None = None,
        user_id: str | None = None,
    ):
        """Add the identity resources to the list of dependencies."""
        if not CONF.multitenant_mode:
            LOG.debug(
                "Multi-tenant mode disabled, identity resources will not "
                "be added as dependencies."
            )
        if project_id:
            associated_resources.append(
                Resource(resource_type="project", source_id=project_id)
            )
        if user_id:
            associated_resources.append(
                Resource(resource_type="user", source_id=user_id)
            )

    def _get_identity_build_kwargs(
        self,
        migrated_associated_resources: list[MigratedResource],
        source_project_id: str | None = None,
        source_user_id: str | None = None,
        project_id_key: str = "project_id",
        user_id_key: str = "user_id",
    ) -> dict[str, str]:
        """Helper method for obtaining identity parameters.

        These parameters specify the owner of the resource that is about
        to be created on the destination cloud.

        The IDs are retrieved from the list of associated resources since
        in multi-tenant mode, the identity resources are reported as
        dependencies.
        """
        kwargs: dict[str, str] = {}
        if not CONF.multitenant_mode:
            LOG.debug("Skipped identity kwargs, multi-tenant mode disabled.")
            return kwargs

        if source_project_id:
            dest_project_id = self._get_associated_resource_destination_id(
                "project", source_project_id, migrated_associated_resources
            )
            kwargs[project_id_key] = dest_project_id

        if source_user_id:
            dest_user_id = self._get_associated_resource_destination_id(
                "user", source_user_id, migrated_associated_resources
            )
            kwargs[user_id_key] = dest_user_id

        LOG.debug("Identity build kwargs: %s", kwargs)
        return kwargs

    def _validate_resource_filters(self, resource_filters: dict[str, str]):
        for key in resource_filters:
            if key not in self.get_supported_resource_filters():
                raise exception.InvalidInput(
                    f"Invalid resource filter: {key}, "
                    f"supported filters {self.get_supported_resource_filters()}"
                )

    def _get_associated_resource_destination_id(
        self,
        resource_type: str,
        source_id: str,
        migrated_associated_resources: list[MigratedResource],
    ) -> str:
        for resource in migrated_associated_resources:
            if (
                resource_type == resource.resource_type
                and source_id == resource.source_id
            ):
                return resource.destination_id
        raise exception.NotFound(
            "Couldn't find migrated associated resource: %s %s - %s. "
            "Please migrate it first or rerun the command with '--include-dependencies'"
            % (resource_type, source_id, migrated_associated_resources)
        )

    def set_manager(self, manager):
        """Pass a manager reference.

        Some migration handlers need a back reference to the migration manager
        to transfer auxiliary resources. For example, volume migrations can consist in
        uploading the volume to Glance, migrating the Glance image and then recreating
        the volume on the destination side using the migrated image.

        We did consider having a migration handler API for auxiliary resources, however
        the idea was dismissed due to the increased complexity.
        """
        self._manager = manager

    @property
    def manager(self):
        """Access the migration manager."""
        if not self._manager:
            raise exception.SunbeamMigrateException(
                "Missing migration manager reference."
            )
        return self._manager
