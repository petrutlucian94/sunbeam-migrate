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
