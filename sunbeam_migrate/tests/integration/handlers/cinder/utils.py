# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils


def create_test_volume_type(
    session,
    *,
    name: str | None = None,
    extra_specs: dict[str, str] | None = None,
    **overrides,
):
    volume_type_kwargs = {
        "name": name or test_utils.get_test_resource_name(),
        "is_public": True,
        "description": "sunbeam-migrate volume type test",
    }
    volume_type_kwargs.update(overrides)
    volume_type = session.block_storage.create_type(**volume_type_kwargs)
    if extra_specs:
        session.block_storage.update_type_extra_specs(volume_type, **extra_specs)

    # Refresh the volume type information.
    return session.block_storage.get_type(volume_type.id)


def check_migrated_volume_type(source_volume_type, destination_volume_type):
    fields = [
        "name",
        "is_public",
        "description",
        "extra_specs",
    ]
    for field in fields:
        assert getattr(source_volume_type, field, None) == getattr(
            destination_volume_type, field, None
        ), f"{field} attribute mismatch"


def check_migrated_volume(source_volume, destination_volume):
    fields = [
        "name",
        "size",
        "description",
        "volume_image_metadata",
        "is_multiattach",
        "volume_type",
    ]
    for field in fields:
        src_val = getattr(source_volume, field, None)
        dest_val = getattr(destination_volume, field, None)
        assert src_val == dest_val, (
            f"{field} attribute mismatch: {src_val} != {dest_val}"
        )


def delete_volume_type(session, volume_type_id: str):
    session.block_storage.delete_type(volume_type_id, ignore_missing=True)


def delete_volume(session, volume_id: str):
    session.block_storage.delete_volume(volume_id, ignore_missing=True)
