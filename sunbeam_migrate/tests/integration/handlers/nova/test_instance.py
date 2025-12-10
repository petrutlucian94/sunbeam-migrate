# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.cinder import utils as cinder_test_utils
from sunbeam_migrate.tests.integration.handlers.neutron import utils as neutron_utils
from sunbeam_migrate.tests.integration.handlers.nova import utils as nova_utils

LOG = logging.getLogger()


def _create_test_instance(
    session,
    flavor_id,
    network,
    image_id,
    security_group=None,
    keypair=None,
):
    """Create a test instance."""
    instance_kwargs = {
        "name": test_utils.get_test_resource_name(),
        "image_id": image_id,
        "flavor_id": flavor_id,
        "networks": [{"uuid": network.id}],
    }

    if security_group:
        instance_kwargs["security_groups"] = [
            {
                "name": security_group.name,
            }
        ]

    if keypair:
        instance_kwargs["key_name"] = keypair.name

    LOG.info("Creating instance: %s", instance_kwargs)
    instance = session.compute.create_server(**instance_kwargs)
    LOG.info("Created instance: %s, waiting for it to become active.", instance.id)
    # Wait for instance to be active
    session.compute.wait_for_server(
        instance,
        status="ACTIVE",
        failures=["ERROR"],
        interval=5,
        wait=300,
    )
    LOG.info("Instance active: %s", instance.id)
    # Refresh instance information
    return session.compute.get_server(instance.id)


def _check_migrated_instance(
    source_instance, destination_instance, source_session, destination_session
):
    """Check that the migrated instance matches the source instance."""
    assert source_instance.name == destination_instance.name, "name mismatch"

    source_flavor = source_session.compute.find_flavor(source_instance.flavor.name)
    dest_flavor = destination_session.compute.find_flavor(source_instance.flavor.name)
    nova_utils.check_migrated_flavor(source_flavor, dest_flavor)

    if source_instance.key_name:
        assert destination_instance.key_name == source_instance.key_name, (
            "keypair name mismatch"
        )

    # TODO: validate the volume attachments and ports.


def _create_test_instance_from_volume(
    session,
    flavor_id,
    network,
    boot_volume_id,
    additional_volume_id=None,
):
    """Create a test instance booted from volume."""
    block_device_mapping = [
        {
            "boot_index": 0,
            "uuid": boot_volume_id,
            "source_type": "volume",
            "destination_type": "volume",
            "delete_on_termination": False,
        }
    ]

    if additional_volume_id:
        block_device_mapping.append(
            {
                "boot_index": 1,
                "uuid": additional_volume_id,
                "source_type": "volume",
                "destination_type": "volume",
                "delete_on_termination": False,
            }
        )

    instance_kwargs = {
        "name": test_utils.get_test_resource_name(),
        "flavor_id": flavor_id,
        "block_device_mapping_v2": block_device_mapping,
        "networks": [{"uuid": network.id}],
    }

    LOG.info("Creating instance from volume: %s", instance_kwargs)
    instance = session.compute.create_server(**instance_kwargs)
    LOG.info("Created instance: %s, waiting for it to become active.", instance.id)
    # Wait for instance to be active
    session.compute.wait_for_server(
        instance,
        status="ACTIVE",
        failures=["ERROR"],
        interval=5,
        wait=300,
    )
    LOG.info("Instance active: %s", instance.id)
    # Refresh instance information
    return session.compute.get_server(instance.id)


def _delete_instance(session, instance):
    session.compute.delete_server(instance.id, ignore_missing=True)
    session.compute.wait_for_delete(instance)


def test_migrate_instance_booted_from_image(
    request,
    base_config,
    test_config,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    """Test instance migration with all associated resources."""
    assert base_config.image_id, "test_config.image_id is required"
    assert base_config.flavor_id, "test_config.flavor_id is required"

    # Create network and subnet on source
    network = neutron_utils.create_test_network(test_source_session)
    request.addfinalizer(lambda: test_source_session.network.delete_network(network.id))

    subnet = neutron_utils.create_test_subnet(
        test_source_session, network, cidr="10.0.0.0/24"
    )
    request.addfinalizer(lambda: test_source_session.network.delete_subnet(subnet.id))

    # Create security group
    security_group = neutron_utils.create_test_security_group(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.network.delete_security_group(security_group.id)
    )

    # Create keypair
    keypair = nova_utils.create_test_keypair(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.compute.delete_keypair(
            keypair.id, ignore_missing=True
        )
    )

    # Create instance
    instance = _create_test_instance(
        test_source_session,
        base_config.flavor_id,
        network,
        image_id=base_config.image_id,
        security_group=security_group,
        keypair=keypair,
    )
    request.addfinalizer(lambda: _delete_instance(test_source_session, instance))

    # Migrate instance with dependencies
    test_utils.call_migrate(
        test_config_path,
        [
            "start",
            "--resource-type=instance",
            "--include-dependencies",
            instance.id,
        ],
    )

    # Verify migrated resources exist
    dest_network = test_destination_session.network.find_network(network.name)
    assert dest_network, "network was not migrated"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(dest_network.id)
    )

    dest_subnet = test_destination_session.network.find_subnet(subnet.name)
    assert dest_subnet, "subnet was not migrated"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(dest_subnet.id)
    )

    dest_sg = test_destination_session.network.find_security_group(security_group.name)
    assert dest_sg, "security group was not migrated"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_security_group(dest_sg.id)
    )

    # Get migrated instance ID from migration record
    dest_instance_id = test_utils.get_destination_resource_id(
        test_config_path, "instance", instance.id
    )
    dest_instance = test_destination_session.compute.get_server(dest_instance_id)
    assert dest_instance, "instance was not migrated"
    request.addfinalizer(
        lambda: _delete_instance(test_destination_session, dest_instance)
    )

    # Cleanup explicitly created ports.
    for port in test_destination_session.network.ports(device_id=dest_instance.id):
        request.addfinalizer(
            lambda: test_destination_session.network.delete_port(
                port.id, ignore_missing=True
            )
        )

    _check_migrated_instance(
        instance, dest_instance, test_source_session, test_destination_session
    )


def test_migrate_instance_booted_from_volume(
    request,
    base_config,
    test_config,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    """Test instance migration booted from volume with additional volume."""
    assert base_config.image_id, "test_config.image_id is required"
    assert base_config.flavor_id, "test_config.flavor_id is required"

    # Create network and subnet on source
    network = neutron_utils.create_test_network(test_source_session)
    request.addfinalizer(lambda: test_source_session.network.delete_network(network.id))

    subnet = neutron_utils.create_test_subnet(
        test_source_session, network, cidr="10.0.1.0/24"
    )
    request.addfinalizer(lambda: test_source_session.network.delete_subnet(subnet.id))

    # Create bootable volume from image
    boot_volume = test_source_session.create_volume(
        name=test_utils.get_test_resource_name(),
        size=1,
        image_id=base_config.image_id,
    )
    request.addfinalizer(
        lambda: cinder_test_utils.delete_volume(test_source_session, boot_volume.id)
    )
    test_source_session.block_storage.wait_for_status(
        boot_volume,
        status="available",
        failures=["error"],
        interval=5,
        wait=300,
    )

    # Create additional non-bootable volume
    additional_volume = test_source_session.create_volume(
        name=test_utils.get_test_resource_name(),
        size=1,
    )
    request.addfinalizer(
        lambda: cinder_test_utils.delete_volume(
            test_source_session, additional_volume.id
        )
    )
    test_source_session.block_storage.wait_for_status(
        additional_volume,
        status="available",
        failures=["error"],
        interval=5,
        wait=300,
    )

    # Create instance booted from volume
    instance = _create_test_instance_from_volume(
        test_source_session,
        base_config.flavor_id,
        network,
        boot_volume.id,
        additional_volume_id=additional_volume.id,
    )
    request.addfinalizer(lambda: _delete_instance(test_source_session, instance))

    # Migrate instance with dependencies
    test_utils.call_migrate(
        test_config_path,
        [
            "start",
            "--resource-type=instance",
            "--include-dependencies",
            instance.id,
        ],
    )

    # Verify migrated resources exist
    dest_network = test_destination_session.network.find_network(network.name)
    assert dest_network, "network was not migrated"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_network(dest_network.id)
    )

    dest_subnet = test_destination_session.network.find_subnet(subnet.name)
    assert dest_subnet, "subnet was not migrated"
    request.addfinalizer(
        lambda: test_destination_session.network.delete_subnet(dest_subnet.id)
    )

    # Verify volumes were migrated
    dest_boot_volume = test_destination_session.block_storage.find_volume(
        boot_volume.name
    )
    assert dest_boot_volume, "boot volume was not migrated"
    request.addfinalizer(
        lambda: cinder_test_utils.delete_volume(
            test_destination_session, dest_boot_volume.id
        )
    )

    dest_additional_volume = test_destination_session.block_storage.find_volume(
        additional_volume.name
    )
    assert dest_additional_volume, "additional volume was not migrated"
    request.addfinalizer(
        lambda: cinder_test_utils.delete_volume(
            test_destination_session, dest_additional_volume.id
        )
    )

    # Get migrated instance ID from migration record
    dest_instance_id = test_utils.get_destination_resource_id(
        test_config_path, "instance", instance.id
    )
    dest_instance = test_destination_session.compute.get_server(dest_instance_id)
    assert dest_instance, "instance was not migrated"
    request.addfinalizer(
        lambda: _delete_instance(test_destination_session, dest_instance)
    )

    # Cleanup explicitly created ports.
    for port in test_destination_session.network.ports(device_id=dest_instance.id):
        request.addfinalizer(
            lambda: test_destination_session.network.delete_port(
                port.id, ignore_missing=True
            )
        )

    _check_migrated_instance(
        instance, dest_instance, test_source_session, test_destination_session
    )
