# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils


def _create_test_image(session):
    image = session.create_image(
        name=test_utils.get_test_resource_name(),
        container="bare",
        disk_format="raw",
        data=bytes([1] * 16 * 1024),
    )
    # Refresh image information.
    return session.get_image(image.id)


def _check_migrated_image(source_image, destination_image):
    for field in ["name", "container_format", "disk_format", "checksum", "size"]:
        source_attr = getattr(source_image, field)
        dest_attr = getattr(destination_image, field)
        assert source_attr == dest_attr, (
            f"{field} attribute mismatch: {source_attr} != {dest_attr}"
        )


def test_migrate_image(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    image = _create_test_image(test_source_session)
    request.addfinalizer(lambda: test_source_session.delete_image(image.id))

    test_utils.call_migrate(
        test_config_path, ["start", "--resource-type=image", image.id]
    )

    dest_image = test_destination_session.image.find_image(image.name)
    assert dest_image, "couldn't find migrated resource"
    request.addfinalizer(lambda: test_destination_session.delete_image(dest_image.id))

    _check_migrated_image(image, dest_image)

    test_utils.call_migrate(
        test_config_path,
        ["cleanup-source", "--resource-type=image", "--source-id", image.id],
    )

    assert not test_source_session.image.find_image(image.id), (
        "cleanup-source didn't remove the resource"
    )


def test_migrate_image_and_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    image = _create_test_image(test_source_session)
    request.addfinalizer(lambda: test_source_session.delete_image(image.id))

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=image", "--cleanup-source", image.id],
    )

    dest_image = test_destination_session.image.find_image(image.name)
    assert dest_image, "couldn't find migrated resource"
    request.addfinalizer(lambda: test_destination_session.delete_image(dest_image.id))

    assert not test_source_session.image.find_image(image.id), (
        "cleanup-source didn't remove the resource"
    )

    _check_migrated_image(image, dest_image)


def test_migrate_image_batch(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_source_project,
):
    image_count = 3
    source_images = []
    for idx in range(image_count):
        image = _create_test_image(test_source_session)
        request.addfinalizer(lambda: test_source_session.delete_image(image))
        source_images.append(image)

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=image",
            "--filter",
            f"owner-id:{test_source_project.id}",
            "--cleanup-source",
        ],
    )

    for image in source_images:
        dest_image = test_destination_session.image.find_image(image.name)
        assert dest_image, "couldn't find migrated resource"
        request.addfinalizer(
            lambda: test_destination_session.delete_image(dest_image.id)
        )

        _check_migrated_image(image, dest_image)

        assert not test_source_session.image.find_image(image.id), (
            "cleanup-source didn't remove the resource"
        )
