# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.cinder import utils as cinder_test_utils


def test_migrate_volume_type_with_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    extra_specs = {"read_only": "false"}
    volume_type = cinder_test_utils.create_test_volume_type(
        test_source_session, extra_specs=extra_specs
    )
    request.addfinalizer(
        lambda: cinder_test_utils.delete_volume_type(
            test_source_session, volume_type.id
        )
    )

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=volume-type", "--cleanup-source", volume_type.id],
    )

    dest_volume_type = test_destination_session.block_storage.find_type(
        volume_type.name
    )
    assert dest_volume_type, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: cinder_test_utils.delete_volume_type(
            test_destination_session, dest_volume_type.id
        )
    )

    cinder_test_utils.check_migrated_volume_type(volume_type, dest_volume_type)

    assert not test_source_session.block_storage.find_type(volume_type.id), (
        "cleanup-source didn't remove the resource"
    )
