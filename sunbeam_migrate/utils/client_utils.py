# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from manilaclient import client as manila_client


def get_manila_client(sdk_session):
    """Obtain a python-manilaclient client from an SDK session.

    The Openstack SDK does not currently support all the Manila APIs
    (e.g. share types). When necessary, we'll use the python-manilaclient
    package instead.
    """
    return manila_client.Client("2", session=sdk_session.session)
