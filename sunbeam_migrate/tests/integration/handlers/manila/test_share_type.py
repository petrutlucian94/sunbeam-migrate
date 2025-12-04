# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from manilaclient import client as manila_client
from manilaclient import exceptions as manila_exc

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.manila import utils as manila_test_utils


def _get_manila_client(session):
    """Get a manilaclient instance from an OpenStack SDK session."""
    return manila_client.Client("2", session=session.auth)


def test_migrate_share_type_with_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    extra_specs = {"driver_handles_share_servers": "false"}
    share_type = manila_test_utils.create_test_share_type(
        test_source_session, extra_specs=extra_specs
    )
    request.addfinalizer(
        lambda: manila_test_utils.delete_share_type(test_source_session, share_type.id)
    )

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=share-type", "--cleanup-source", share_type.id],
    )

    dest_manila = _get_manila_client(test_destination_session)
    dest_share_types = dest_manila.share_types.list(
        search_opts={"name": share_type.name}
    )
    assert dest_share_types, "couldn't find migrated resource"
    dest_share_type = dest_share_types[0]
    request.addfinalizer(
        lambda: manila_test_utils.delete_share_type(
            test_destination_session, dest_share_type.id
        )
    )

    manila_test_utils.check_migrated_share_type(share_type, dest_share_type)

    source_manila = _get_manila_client(test_source_session)
    try:
        source_manila.share_types.get(share_type.id)
        assert False, "cleanup-source didn't remove the resource"
    except manila_exc.NotFound:
        # Expected - resource was deleted
        pass
