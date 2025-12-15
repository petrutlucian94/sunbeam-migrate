# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.nova import utils as nova_utils


def _check_migrated_keypair(source_keypair, destination_keypair, destination_session):
    """Check that the migrated keypair matches the source keypair."""
    for field in ["name", "type", "fingerprint"]:
        source_val = getattr(source_keypair, field, None)
        dest_val = getattr(destination_keypair, field, None)
        assert source_val == dest_val, f"{field} mismatch, {source_val} != {dest_val}"


def _delete_keypair(session, keypair_id: str):
    session.compute.delete_keypair(keypair_id, ignore_missing=True)


def test_migrate_keypair_with_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_requester_source_session,
    test_requester_destination_session,
):
    keypair = nova_utils.create_test_keypair(test_requester_source_session)
    request.addfinalizer(lambda: _delete_keypair(test_requester_source_session, keypair.id))

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=keypair", "--cleanup-source", keypair.id],
    )

    dest_keypair = test_requester_destination_session.compute.find_keypair(keypair.name)
    assert dest_keypair, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: _delete_keypair(test_requester_destination_session, dest_keypair.id)
    )

    _check_migrated_keypair(keypair, dest_keypair, test_requester_destination_session)

    # Check that the keypair was removed from source
    assert not test_requester_source_session.compute.find_keypair(
        keypair.name, ignore_missing=True
    ), "cleanup-source didn't remove the resource"


def test_migrate_keypair_skips_existing_destination(
    request,
    test_config_path,
    test_credentials,
    test_requester_source_session,
    test_requester_destination_session,
):
    shared_name = test_utils.get_test_resource_name()

    source_keypair = nova_utils.create_test_keypair(
        test_requester_source_session,
        name=shared_name,
    )
    request.addfinalizer(
        lambda: _delete_keypair(test_requester_source_session, source_keypair.id)
    )

    destination_keypair = nova_utils.create_test_keypair(
        test_requester_destination_session,
        name=shared_name,
    )
    request.addfinalizer(
        lambda: _delete_keypair(test_requester_destination_session, destination_keypair.id)
    )

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=keypair", source_keypair.id],
    )

    migrated_dest_id = test_utils.get_destination_resource_id(
        test_config_path, "keypair", source_keypair.id
    )
    assert migrated_dest_id == destination_keypair.id, (
        "migration should reuse the existing destination keypair"
    )
