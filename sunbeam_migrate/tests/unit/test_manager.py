# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from unittest import mock

import pytest

from sunbeam_migrate import constants, exception, manager
from sunbeam_migrate.handlers.base import Resource


@mock.patch("sunbeam_migrate.handlers.factory.get_migration_handler")
@mock.patch("sunbeam_migrate.db.api.get_migrations")
@mock.patch("sunbeam_migrate.db.models.Migration.save")
def _test_individual_migration(
    mock_migration_cls_save,
    mock_get_migrations,
    mock_get_migration_handler,
    cleanup_source=False,
    include_members=False,
    include_dependencies=False,
    has_dependencies=True,
    dry_run=False,
):
    mock_handler = mock_get_migration_handler.return_value
    mock_handler.get_service_type.return_value = "fake-service-type"

    migrated_resources = set()

    def _fake_get_migrations(
        order_by="created_at",
        ascending=False,
        session=None,
        include_archived=False,
        source_id=None,
        resource_type=None,
    ):
        if source_id in migrated_resources:
            return [mock.Mock(status=constants.STATUS_COMPLETED)]
        return []

    def _fake_migrate_resource(
        resource_id,
        migrated_associated_resources,
    ):
        migrated_resources.add(resource_id)

    def _fake_get_associated_resources(resource_id):
        if has_dependencies and resource_id == "fake-instance":
            return [
                Resource(
                    resource_type="volume",
                    source_id="fake-volume",
                    should_cleanup=True,
                ),
                Resource(
                    resource_type="flavor",
                    source_id="fake-flavor",
                    should_cleanup=False,
                ),
            ]
        return []

    def _fake_get_member_resources(resource_id):
        if resource_id == "fake-instance":
            return [
                Resource(
                    resource_type="subnet",
                    source_id="fake-subnet",
                ),
            ]
        else:
            return []

    mock_get_migrations.side_effect = _fake_get_migrations
    mock_handler.perform_individual_migration.side_effect = _fake_migrate_resource
    mock_handler.get_associated_resources.side_effect = _fake_get_associated_resources
    mock_handler.get_member_resources.side_effect = _fake_get_member_resources

    mgr = manager.SunbeamMigrationManager()

    migration = mgr.perform_individual_migration(
        resource_type="instance",
        resource_id="fake-instance",
        cleanup_source=cleanup_source,
        include_members=include_members,
        include_dependencies=include_dependencies,
        dry_run=dry_run,
    )

    if dry_run:
        mock_handler.perform_individual_migration.assert_not_called()
        mock_handler.delete_source_resource.assert_not_called()
    else:
        assert migration.service == "fake-service-type"
        assert migration.resource_type == "instance"
        assert migration.source_id == "fake-instance"
        assert migration.status == constants.STATUS_COMPLETED

        mock_handler.perform_individual_migration.assert_any_call(
            "fake-instance",
            migrated_associated_resources=mock.ANY,
        )

    if has_dependencies and include_dependencies and not dry_run:
        mock_handler.perform_individual_migration.assert_any_call(
            "fake-volume",
            migrated_associated_resources=mock.ANY,
        )
        mock_handler.perform_individual_migration.assert_any_call(
            "fake-flavor",
            migrated_associated_resources=mock.ANY,
        )
        if cleanup_source:
            mock_handler.delete_source_resource.assert_any_call("fake-volume")

        # shared resource, shouldn't be cleaned up
        assert (
            mock.call("fake-flavor")
            not in mock_handler.delete_source_resource.call_args_list
        )

    if include_members and not dry_run:
        mock_handler.perform_individual_migration.assert_any_call(
            "fake-subnet",
            migrated_associated_resources=mock.ANY,
        )
        mock_handler.connect_member_resources_to_parent.assert_any_call(
            parent_resource_id=mock.ANY, migrated_member_resources=mock.ANY
        )

    if cleanup_source and not dry_run:
        mock_handler.delete_source_resource.assert_any_call("fake-instance")
    else:
        mock_handler.delete_source_resource.assert_not_called()


def test_migrate_individual_resource_no_dependencies():
    _test_individual_migration(has_dependencies=False, include_dependencies=False)


def test_migrate_individual_resource_missing_dependencies():
    with pytest.raises(exception.InvalidInput):
        _test_individual_migration(has_dependencies=True, include_dependencies=False)


def test_migrate_individual_resource_with_members():
    _test_individual_migration(include_members=True, include_dependencies=True)


def test_migrate_individual_resource_with_deps_and_cleanup():
    _test_individual_migration(
        include_members=True,
        include_dependencies=True,
        cleanup_source=True,
    )


def test_migrate_individual_resource_dry_run():
    _test_individual_migration(
        include_members=True,
        include_dependencies=True,
        cleanup_source=True,
        dry_run=True,
    )


@mock.patch("sunbeam_migrate.handlers.factory.get_migration_handler")
@mock.patch("sunbeam_migrate.db.api.get_migrations")
@mock.patch("sunbeam_migrate.db.models.Migration.save")
@mock.patch(
    "sunbeam_migrate.manager.SunbeamMigrationManager.perform_individual_migration"
)
def test_perform_batch_migration(
    mock_individual_migration,
    mock_migration_cls_save,
    mock_get_migrations,
    mock_get_migration_handler,
):
    mock_handler = mock_get_migration_handler.return_value
    mock_handler.get_service_type.return_value = "fake-service-type"

    mock_get_migrations.side_effect = [None, None, [mock.Mock()]]
    fake_resources = [
        mock.sentinel.resource_id_0,
        mock.sentinel.resource_id_1,
        mock.sentinel.resource_id_2,  # Already migrated.
    ]
    fake_resources_to_migrate = [
        mock.sentinel.resource_id_0,
        mock.sentinel.resource_id_1,
    ]
    mock_handler.get_source_resource_ids.return_value = fake_resources

    mgr = manager.SunbeamMigrationManager()
    mgr.perform_batch_migration(
        resource_type=mock.sentinel.resource_type,
        resource_filters=mock.sentinel.resource_filters,
        cleanup_source=mock.sentinel.cleanup_source,
        include_members=mock.sentinel.include_members,
        include_dependencies=mock.sentinel.include_dependencies,
        dry_run=mock.sentinel.dry_run,
    )

    for fake_resource in fake_resources_to_migrate:
        mock_individual_migration.assert_any_call(
            mock.sentinel.resource_type,
            fake_resource,
            cleanup_source=mock.sentinel.cleanup_source,
            include_members=mock.sentinel.include_members,
            include_dependencies=mock.sentinel.include_dependencies,
            dry_run=mock.sentinel.dry_run,
        )

    mock_handler.get_source_resource_ids.assert_called_once_with(
        mock.sentinel.resource_filters
    )
