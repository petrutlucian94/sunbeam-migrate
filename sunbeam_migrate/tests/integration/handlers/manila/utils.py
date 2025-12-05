# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from manilaclient import exceptions as manila_exc

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.utils import client_utils


def create_test_share_type(
    session,
    *,
    name: str | None = None,
    extra_specs: dict[str, str] | None = None,
    **overrides,
):
    manila = client_utils.get_manila_client(session)
    share_type_kwargs = {
        "name": name or test_utils.get_test_resource_name(),
        "is_public": True,
        "spec_driver_handles_share_servers": False,
    }
    share_type_kwargs.update(overrides)
    share_type = manila.share_types.create(**share_type_kwargs)
    if extra_specs:
        share_type.set_keys(extra_specs)

    # Refresh the share type information.
    return manila.share_types.get(share_type.id)


def check_migrated_share_type(source_share_type, destination_share_type):
    fields = [
        "name",
        "is_public",
        "extra_specs",
    ]
    for field in fields:
        assert getattr(source_share_type, field, None) == getattr(
            destination_share_type, field, None
        ), f"{field} attribute mismatch"


def delete_share_type(session, share_type_id: str):
    manila = client_utils.get_manila_client(session)
    try:
        manila.share_types.delete(share_type_id)
    except manila_exc.NotFound:
        pass


def create_test_share(
    session,
    *,
    name: str | None = None,
    size: int = 1,
    share_protocol: str = "NFS",
    share_type: str | None = None,
    description: str | None = None,
    **overrides,
):
    share_kwargs = {
        "name": name or test_utils.get_test_resource_name(),
        "size": size,
        "share_protocol": share_protocol,
        "description": description or "sunbeam-migrate share test",
    }
    if share_type:
        share_kwargs["share_type"] = share_type
    share_kwargs.update(overrides)
    share = session.shared_file_system.create_share(**share_kwargs)

    # Wait for share to be available
    session.shared_file_system.wait_for_status(
        share,
        status="available",
        failures=["error"],
        interval=5,
        wait=300,
    )

    # Refresh the share information.
    return session.shared_file_system.get_share(share.id)


def check_migrated_share(source_share, destination_share):
    fields = [
        "name",
        "size",
        "share_protocol",
        "description",
        "share_type_name",
    ]
    for field in fields:
        source_val = getattr(source_share, field, None)
        destination_val = getattr(destination_share, field, None)
        assert source_val == destination_val, (
            f"{field} attribute mismatch: {source_val} != {destination_val}"
        )


def delete_share(session, share_id: str):
    session.shared_file_system.delete_share(share_id, ignore_missing=True)
