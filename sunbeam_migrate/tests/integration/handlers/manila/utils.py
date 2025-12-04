# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from manilaclient import client as manila_client
from manilaclient import exceptions as manila_exc

from sunbeam_migrate.tests.integration import utils as test_utils


def _get_manila_client(session):
    """Get a manilaclient instance from an OpenStack SDK session."""
    return manila_client.Client("2", session=session.auth)


def create_test_share_type(
    session,
    *,
    name: str | None = None,
    extra_specs: dict[str, str] | None = None,
    **overrides,
):
    manila = _get_manila_client(session)
    share_type_kwargs = {
        "name": name or test_utils.get_test_resource_name(),
        "is_public": True,
        "description": "sunbeam-migrate share type test",
    }
    share_type_kwargs.update(overrides)
    share_type = manila.share_types.create(**share_type_kwargs)
    if extra_specs:
        manila.share_types.set_keys(share_type, extra_specs)

    # Refresh the share type information.
    return manila.share_types.get(share_type.id)


def check_migrated_share_type(source_share_type, destination_share_type):
    fields = [
        "name",
        "is_public",
        "description",
        "extra_specs",
    ]
    for field in fields:
        assert getattr(source_share_type, field, None) == getattr(
            destination_share_type, field, None
        ), f"{field} attribute mismatch"


def delete_share_type(session, share_type_id: str):
    manila = _get_manila_client(session)
    try:
        manila.share_types.delete(share_type_id)
    except manila_exc.NotFound:
        # Already deleted or doesn't exist
        pass
