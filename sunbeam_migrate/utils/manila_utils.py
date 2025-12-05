# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import contextlib
import logging
import os
import re
import socket
import subprocess
from collections.abc import Generator

from openstack import exceptions as openstack_exc

from sunbeam_migrate import config, exception

CONF = config.get_config()
LOG = logging.getLogger()


def get_share_export_path(sdk_conn, share_id: str) -> str:
    export_locations = sdk_conn.shared_file_system.export_locations(share_id)
    if not export_locations:
        raise exception.NotFound("No share export found.")
    export_locations = sorted(
        export_locations, key=lambda x: x.is_preferred, reverse=True
    )
    return export_locations[0].path


def _get_local_ip_for_remote(remote_ip: str) -> str:
    cmd = ["ip", "route", "get", remote_ip]
    # Determine which local IP will be used to contact the specified remote IP.
    output = subprocess.check_output(cmd, text=True)
    # Output examples:
    #   local 192.168.99.206 dev lo table local src 192.168.99.206 uid 1000
    #   8.8.8.8 via 192.168.30.1 dev eth0 src 192.168.99.206 uid 1000
    ips = re.findall(r"src ([\w.:]+)", output)
    if not ips:
        raise exception.NotFound(f"Unable to determine the route to {remote_ip}.")
    return ips[0]


@contextlib.contextmanager
def temporary_share_access(sdk_conn, share, export_path: str, access_level="rw"):
    if CONF.manila_local_access_ip:
        access_ip = CONF.manila_local_access_ip
    else:
        export_address = export_path.split("/", 1)[0].strip(":")
        export_ip = socket.gethostbyname(export_address)
        access_ip = _get_local_ip_for_remote(export_ip)

    try:
        existing_rules = sdk_conn.shared_file_system.access_rules(share)
        for rule in existing_rules:
            if (
                rule.access_to == access_ip
                and rule.access_level == access_level
                and rule.access_type == "ip"
            ):
                LOG.info("Share access already provided: %s", rule.id)
                yield
                return
    except openstack_exc.NotFoundException:
        # No access rules have been defined yet.
        pass

    try:
        LOG.info("Adding temporary share access rule: %s to ip %s", share.id, access_ip)
        access_rule = sdk_conn.shared_file_system.create_access_rule(
            share.id, access_to=access_ip, access_type="ip", access_level=access_level
        )
        LOG.info("Waiting for share access rule to become active.")
        sdk_conn.shared_file_system.wait_for_status(
            access_rule,
            status="active",
            attribute="state",
            failures=["error"],
            interval=5,
            wait=CONF.resource_creation_timeout,
        )
        yield
    finally:
        LOG.info(
            "Deleting temporary share access rule: %s to ip %s", share.id, access_ip
        )
        sdk_conn.shared_file_system.delete_access_rule(access_rule.id, share.id)


@contextlib.contextmanager
def mounted_nfs_share(sdk_conn, share, access_level="rw") -> Generator[str]:
    export_path = get_share_export_path(sdk_conn, share.id)

    base_dir = CONF.temporary_migration_dir
    mount_dirname = f"{share.id}.{int.from_bytes(os.urandom(4))}"
    mountpoint = str(base_dir / mount_dirname)
    os.makedirs(mountpoint)

    with temporary_share_access(sdk_conn, share, export_path, access_level):
        mount_nfs_share(export_path, mountpoint)
        try:
            yield mountpoint
        finally:
            unmount_nfs_share(mountpoint)
            os.rmdir(mountpoint)


def mount_nfs_share(export_path: str, mountpoint: str):
    LOG.info("Mounting nfs share %s to %s.", export_path, mountpoint)
    cmd = ["sudo", "mount", "-v", "-t", "nfs", export_path, mountpoint]
    subprocess.check_call(cmd, text=True)


def unmount_nfs_share(mountpoint: str):
    LOG.info("Unmounting nfs share: %s", mountpoint)
    cmd = ["sudo", "umount", "-f", mountpoint]
    subprocess.check_call(cmd, text=True)
