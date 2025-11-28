# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils


def _create_test_flavor(
    session,
    *,
    name: str | None = None,
    extra_specs: dict[str, str] | None = None,
    **overrides,
):
    flavor_name = name or test_utils.get_test_resource_name()
    flavor_kwargs = {
        "name": flavor_name,
        "ram": 512,
        "vcpus": 1,
        "disk": 1,
        "swap": 256,
        "ephemeral": 1,
        "rxtx_factor": 1.25,
        "is_public": False,
        "description": "sunbeam-migrate flavor test",
    }
    flavor_kwargs.update(overrides)
    if not extra_specs:
        extra_specs = {"hw:cpu_policy": "dedicated"}

    flavor = session.compute.create_flavor(**flavor_kwargs)
    session.compute.create_flavor_extra_specs(flavor, extra_specs)

    # Refresh the flavor information.
    return session.compute.get_flavor(flavor.id)


def _check_migrated_flavor(source_flavor, destination_flavor, destination_session):
    fields = [
        "name",
        "ram",
        "vcpus",
        "disk",
        "swap",
        "ephemeral",
        "rxtx_factor",
        "is_public",
        "description",
    ]
    for field in fields:
        assert getattr(source_flavor, field, None) == getattr(
            destination_flavor, field, None
        ), f"{field} attribute mismatch"

    source_specs = getattr(source_flavor, "extra_specs", {})
    dest_specs = getattr(destination_flavor, "extra_specs", {})
    assert dest_specs == source_specs


def _delete_flavor(session, flavor_id: str):
    session.compute.delete_flavor(flavor_id, ignore_missing=True)


def test_migrate_flavor(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    flavor = _create_test_flavor(test_source_session)
    request.addfinalizer(lambda: _delete_flavor(test_source_session, flavor.id))

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=flavor", flavor.id],
    )

    dest_flavor = test_destination_session.compute.find_flavor(flavor.name)
    assert dest_flavor, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: _delete_flavor(test_destination_session, dest_flavor.id)
    )

    _check_migrated_flavor(flavor, dest_flavor, test_destination_session)


def test_migrate_flavor_with_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    flavor = _create_test_flavor(test_source_session)
    request.addfinalizer(lambda: _delete_flavor(test_source_session, flavor.id))

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=flavor", "--cleanup-source", flavor.id],
    )

    dest_flavor = test_destination_session.compute.find_flavor(flavor.name)
    assert dest_flavor, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: _delete_flavor(test_destination_session, dest_flavor.id)
    )

    _check_migrated_flavor(flavor, dest_flavor, test_destination_session)

    assert not test_source_session.compute.find_flavor(flavor.id), (
        "cleanup-source didn't remove the resource"
    )


def test_migrate_flavor_skips_existing_destination(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    shared_name = test_utils.get_test_resource_name()

    source_flavor = _create_test_flavor(
        test_source_session,
        name=shared_name,
    )
    request.addfinalizer(lambda: _delete_flavor(test_source_session, source_flavor.id))

    destination_flavor = _create_test_flavor(
        test_destination_session,
        name=shared_name,
    )
    request.addfinalizer(
        lambda: _delete_flavor(test_destination_session, destination_flavor.id)
    )

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=flavor", source_flavor.id],
    )

    migrated_dest_id = test_utils.get_destination_resource_id(
        test_config_path, "flavor", source_flavor.id
    )
    assert migrated_dest_id == destination_flavor.id, (
        "migration should reuse the existing destination flavor"
    )
