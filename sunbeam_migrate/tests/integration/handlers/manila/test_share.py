# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import json
import subprocess

import pytest
import yaml
from openstack import exceptions as openstack_exc

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.manila import utils as manila_test_utils
from sunbeam_migrate.utils import manila_utils


def test_migrate_share_with_cleanup(
    request,
    test_config,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    # We intend to cover share types, so let's set the following flag.
    test_config.preserve_share_type = True
    with test_config_path.open("w") as f:
        cfg_dict = json.loads(test_config.model_dump_json())
        f.write(yaml.dump(cfg_dict))

    share_type = manila_test_utils.create_test_share_type(test_source_session)
    request.addfinalizer(
        lambda: manila_test_utils.delete_share_type(test_source_session, share_type.id)
    )

    # Create a share with the share type
    share = manila_test_utils.create_test_share(
        test_source_session,
        share_type=share_type.id,
        size=1,
        share_protocol="NFS",
    )
    request.addfinalizer(
        lambda: manila_test_utils.delete_share(test_source_session, share.id)
    )

    # TODO: consider checking symlinks, xattr, timestamps and file ownership.
    test_file_contents = "manila share test"
    with manila_utils.mounted_nfs_share(
        test_source_session, share
    ) as source_mountpoint:
        subprocess.check_call(["sudo", "mkdir", "-p", f"{source_mountpoint}/subdir"])
        subprocess.run(
            ["sudo", "tee", f"{source_mountpoint}/subdir/test_file"],
            input=test_file_contents,
            text=True,
        )

    test_utils.call_migrate(
        test_config_path,
        [
            "start",
            "--resource-type=share",
            "--cleanup-source",
            "--include-dependencies",
            share.id,
        ],
    )

    dest_share = test_destination_session.shared_file_system.find_share(share.name)
    assert dest_share, "couldn't find migrated resource"
    request.addfinalizer(
        lambda: manila_test_utils.delete_share(test_destination_session, dest_share.id)
    )
    # "find_share" doesn't include all properties (e.g. size), let's refresh it.
    dest_share = test_destination_session.shared_file_system.get_share(dest_share.id)

    manila_test_utils.check_migrated_share(share, dest_share)

    with pytest.raises(openstack_exc.ResourceNotFound):
        test_source_session.shared_file_system.get_share(share.id)

    with manila_utils.mounted_nfs_share(
        test_destination_session, dest_share
    ) as destination_mountpoint:
        migrated_contents = subprocess.check_output(
            ["sudo", "cat", f"{destination_mountpoint}/subdir/test_file"], text=True
        )
        assert test_file_contents == migrated_contents
