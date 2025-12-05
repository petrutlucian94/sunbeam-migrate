# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import pytest
from manilaclient import exceptions as manila_exc

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.tests.integration.handlers.manila import utils as manila_test_utils
from sunbeam_migrate.utils import client_utils


def test_migrate_share_type_with_cleanup(
    request,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
):
    extra_specs = {"driver_handles_share_servers": "false"}
    share_type = manila_test_utils.create_test_share_type(
        test_source_session, extra_specs=extra_specs
    )
    request.addfinalizer(
        lambda: manila_test_utils.delete_share_type(test_source_session, share_type.id)
    )

    test_utils.call_migrate(
        test_config_path,
        ["start", "--resource-type=share-type", "--cleanup-source", share_type.id],
    )

    dest_manila = client_utils.get_manila_client(test_destination_session)
    dest_share_types = [
        s_type
        for s_type in dest_manila.share_types.list()
        if share_type.name == s_type.name
    ]
    assert dest_share_types, "couldn't find migrated resource"
    dest_share_type = dest_share_types[0]
    request.addfinalizer(
        lambda: manila_test_utils.delete_share_type(
            test_destination_session, dest_share_type.id
        )
    )

    manila_test_utils.check_migrated_share_type(share_type, dest_share_type)

    source_manila = client_utils.get_manila_client(test_source_session)
    with pytest.raises(manila_exc.NotFound):
        source_manila.share_types.get(share_type.id)
