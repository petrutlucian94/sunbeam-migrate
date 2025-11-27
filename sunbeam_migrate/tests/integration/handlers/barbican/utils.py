# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils
from sunbeam_migrate.utils import barbican_utils


def create_test_secret(request, session, binary=False, **kwargs):
    secret_name = test_utils.get_test_resource_name()
    kwargs["name"] = secret_name

    if binary:
        secret_payload = b"\x01%s-payload\x02" % secret_name
        kwargs["payload"] = base64.b64encode(secret_payload).decode()
        kwargs["payload_content_type"] = "application/octet-stream"
        kwargs["payload_content_encoding"] = "base64"
    else:
        kwargs["payload"] = f"{secret_name}-payload"
        kwargs["payload_content_type"] = "text/plain"

    secret = session.key_manager.create_secret(**kwargs)
    request.addfinalizer(lambda: session.key_manager.delete_secret(secret.secret_id))
    secret = session.key_manager.get_secret(
        barbican_utils.parse_barbican_url(secret.id)
    )
    return secret


def check_migrated_secret(source_secret, destination_secret):
    fields = [
        "algorithm",
        "bit_length",
        "content_types",
        "expires_at",
        "mode",
        "name",
        "secret_type",
        "payload",
    ]
    for field in fields:
        source_attr = getattr(source_secret, field)
        dest_attr = getattr(destination_secret, field)
        assert source_attr == dest_attr, (
            f"{field} attribute mismatch: {source_attr} != {dest_attr}"
        )


def create_test_secret_container(request, session, secrets: list, **kwargs):
    secret_refs = []
    for secret in secrets:
        secret_refs.append(
            {
                "name": secret.name,
                "secret_ref": secret.secret_ref,
            }
        )
    kwargs["secret_refs"] = secret_refs
    secret_container = session.key_manager.create_container(
        name=test_utils.get_test_resource_name(), type="generic", **kwargs
    )
    request.addfinalizer(
        lambda: session.key_manager.delete_container(secret_container.container_id)
    )
    return secret_container


def check_migrated_secret_container(
    test_source_session,
    test_destination_session,
    source_container,
    destination_container,
):
    fields = [
        "name",
        "type",
    ]
    for field in fields:
        source_attr = getattr(source_container, field)
        dest_attr = getattr(destination_container, field)
        assert source_attr and source_attr == dest_attr, f"{field} attribute mismatch"

    source_refs = source_container.secret_refs
    destination_refs = destination_container.secret_refs

    for source_ref in source_refs:
        ref_found = False
        for destination_ref in destination_refs:
            if destination_ref["name"] == source_ref["name"]:
                ref_found = True
                break
        assert ref_found, (
            "The migrated secret container doesn't include secret ref: %s" % source_ref
        )
