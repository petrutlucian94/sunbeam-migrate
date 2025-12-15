# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import json

import yaml

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.cinder import utils as cinder_test_utils

TEST_VOLUME_PAYLOAD = "test-volume-payload".encode()
TEST_VOLUME_SIZE = 1


def _create_test_volume(base_config, session, volume_type: str | None = None):
    # We want to ensure that the volume data gets transferred. For this
    # reason, we'll use an image with a predetermined payload.
    image = session.create_image(
        name=test_utils.get_test_resource_name(),
        container="bare",
        disk_format="raw",
        data=TEST_VOLUME_PAYLOAD,
    )
    volume_kwargs = {}
    if volume_type:
        volume_kwargs["volume_type"] = volume_type
    try:
        volume = session.create_volume(
            name=test_utils.get_test_resource_name(),
            size=TEST_VOLUME_SIZE,
            description="sunbeam-migrate test volume",
            image_id=image.id,
            metadata={
                "testkey": "testval",
            },
            **volume_kwargs,
        )
        session.block_storage.wait_for_status(
            volume,
            status="available",
            failures=["error"],
            interval=5,
            wait=base_config.volume_upload_timeout,
        )
        image_metadata = {
            "ramdisk_id": "81319b73-9acd-41f1-8d83-642063e4531a",
        }
        session.block_storage.set_volume_image_metadata(volume, metadata=image_metadata)
    finally:
        session.delete_image(image.id)

    # Refresh the volume.
    volume = session.block_storage.find_volume(volume.id)
    return volume


def test_migrate_volume_with_cleanup(
    request,
    base_config,
    test_config,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    # We intend to cover volume types, so let's set the following flag.
    test_config.preserve_volume_type = True
    with test_config_path.open("w") as f:
        cfg_dict = json.loads(test_config.model_dump_json())
        f.write(yaml.dump(cfg_dict))

    volume_type = cinder_test_utils.create_test_volume_type(test_source_session)
    request.addfinalizer(
        lambda: cinder_test_utils.delete_volume(test_source_session, volume_type.id)
    )

    volume = _create_test_volume(base_config, test_source_session, volume_type.name)

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=volume",
            "--include-dependencies",
            "--cleanup-source",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_volume = test_destination_session.block_storage.find_volume(volume.name)
    assert dest_volume, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: cinder_test_utils.delete_volume(
            test_destination_session, dest_volume.id
        )
    )

    # Check volume properties.
    cinder_test_utils.check_migrated_volume(volume, dest_volume)

    remaining_source_volume = test_source_session.block_storage.find_volume(volume.id)
    assert (
        not remaining_source_volume or remaining_source_volume.status == "deleting"
    ), "cleanup-source didn't remove the resource"

    # Upload the destination volume to Glance so that we can check the volume
    # contents.
    image_name = test_utils.get_test_resource_name()
    response = test_destination_session.block_storage.upload_volume_to_image(
        dest_volume, image_name, force=True
    )
    image_id = response["image_id"]
    request.addfinalizer(lambda: test_destination_session.delete_image(image_id))

    image = test_destination_session.get_image(image_id)
    test_destination_session.image.wait_for_status(
        image,
        status="active",
        failures=["error"],
        interval=5,
        wait=base_config.volume_upload_timeout,
    )
    response = test_destination_session.image.download_image(image, stream=True)
    first_chunk = next(response.iter_content(chunk_size=1024))
    # We only need the first chunk.
    response.close()
    expected_payload = TEST_VOLUME_PAYLOAD + bytes(
        [0] * (1024 - len(TEST_VOLUME_PAYLOAD))
    )
    assert expected_payload == first_chunk
