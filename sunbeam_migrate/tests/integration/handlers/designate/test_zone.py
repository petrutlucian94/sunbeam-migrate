# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate.tests.integration import utils as test_utils


def _create_test_zone(session, **overrides):
    """Create a test DNS zone."""
    zone_name = test_utils.get_test_resource_name()
    zone_kwargs = {
        "name": f"{zone_name}.example.com.",
        "email": "admin@example.com",
        "ttl": 3600,
        "type": "PRIMARY",
        "description": "Test DNS zone",
    }
    zone_kwargs.update(overrides)
    zone = session.dns.create_zone(**zone_kwargs)
    # Refresh zone information
    return session.dns.get_zone(zone.id)


def _create_test_recordset(session, zone, record_type="A", **overrides):
    """Create a test recordset in a zone."""
    recordset_name = test_utils.get_test_resource_name()

    default_records = {
        "A": ["192.0.2.1"],
        "AAAA": ["2001:db8::1"],
        "CNAME": ["target.example.com."],
        "MX": ["10 mail.example.com."],
        "TXT": ['"v=spf1 include:example.com ~all"'],
    }

    recordset_kwargs = {
        "name": f"{recordset_name}.{zone.name}",
        "type": record_type,
        "records": default_records.get(record_type, ["192.0.2.1"]),
        "ttl": 300,
        "description": f"Test {record_type} recordset",
    }
    recordset_kwargs.update(overrides)
    recordset = session.dns.create_recordset(zone=zone.id, **recordset_kwargs)
    # Refresh recordset information
    return session.dns.get_recordset(recordset=recordset.id, zone=zone.id)


def _check_migrated_zone(source_zone, destination_zone):
    """Verify that zone attributes were migrated correctly."""
    fields = [
        "description",
        "email",
        "name",
        "ttl",
        "type",
    ]
    for field in fields:
        source_attr = getattr(source_zone, field, None)
        dest_attr = getattr(destination_zone, field, None)
        assert source_attr == dest_attr, f"{field} attribute mismatch"


def _check_migrated_recordset(source_recordset, destination_recordset):
    """Verify that recordset attributes were migrated correctly."""
    fields = [
        "description",
        "name",
        "records",
        "ttl",
        "type",
    ]
    for field in fields:
        source_attr = getattr(source_recordset, field, None)
        dest_attr = getattr(destination_recordset, field, None)
        assert source_attr == dest_attr, f"{field} attribute mismatch"


def test_migrate_zone_and_cleanup(
    request,
    test_config,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    """Test zone migration with cleanup-source flag."""
    zone = _create_test_zone(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.dns.delete_zone(zone.id, ignore_missing=True)
    )

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=dns-zone",
            "--include-dependencies",
            "--cleanup-source",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_zone = test_destination_session.dns.find_zone(zone.name)
    assert dest_zone, "couldn't find migrated zone"
    request.addfinalizer(
        lambda: test_destination_session.dns.delete_zone(
            dest_zone.id, ignore_missing=True
        )
    )

    _check_migrated_zone(zone, dest_zone)

    # Verify source zone was deleted or is being deleted (asynchronous)
    source_zone_after = test_source_session.dns.find_zone(zone.id, ignore_missing=True)
    if source_zone_after:
        # Zone still exists, but should be in DELETE state
        assert getattr(source_zone_after, "action", "") == "DELETE", (
            "cleanup-source didn't trigger zone deletion"
        )


def test_migrate_zone_with_recordsets(
    request,
    test_config,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    """Test zone migration with multiple recordsets."""
    zone = _create_test_zone(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.dns.delete_zone(zone.id, ignore_missing=True)
    )

    a_record = _create_test_recordset(test_source_session, zone, record_type="A")
    aaaa_record = _create_test_recordset(test_source_session, zone, record_type="AAAA")
    txt_record = _create_test_recordset(test_source_session, zone, record_type="TXT")

    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=dns-zone",
            "--include-dependencies",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
        ],
    )

    dest_zone = test_destination_session.dns.find_zone(zone.name)
    assert dest_zone, "couldn't find migrated zone"
    request.addfinalizer(
        lambda: test_destination_session.dns.delete_zone(
            dest_zone.id, ignore_missing=True
        )
    )

    _check_migrated_zone(zone, dest_zone)

    # Verify recordsets were migrated (excluding auto-created NS and SOA)
    dest_recordsets = [
        rs
        for rs in test_destination_session.dns.recordsets(zone=dest_zone.id)
        if rs.type not in ["NS", "SOA"]
    ]
    assert len(dest_recordsets) == 3, (
        f"Expected 3 recordsets, found {len(dest_recordsets)}"
    )

    # Verify A record
    dest_a_record = next(
        (rs for rs in dest_recordsets if rs.name == a_record.name), None
    )
    assert dest_a_record, f"A record {a_record.name} not found"
    _check_migrated_recordset(a_record, dest_a_record)

    # Verify AAAA record
    dest_aaaa_record = next(
        (rs for rs in dest_recordsets if rs.name == aaaa_record.name), None
    )
    assert dest_aaaa_record, f"AAAA record {aaaa_record.name} not found"
    _check_migrated_recordset(aaaa_record, dest_aaaa_record)

    # Verify TXT record
    dest_txt_record = next(
        (rs for rs in dest_recordsets if rs.name == txt_record.name), None
    )
    assert dest_txt_record, f"TXT record {txt_record.name} not found"
    _check_migrated_recordset(txt_record, dest_txt_record)


def test_migrate_zone_batch_by_project(
    request,
    test_config,
    test_config_path,
    test_credentials,
    test_source_session,
    test_destination_session,
    test_owner_source_project,
):
    """Test batch migration filtering by project/owner."""
    zone = _create_test_zone(test_source_session)
    request.addfinalizer(
        lambda: test_source_session.dns.delete_zone(zone.id, ignore_missing=True)
    )

    _create_test_recordset(test_source_session, zone, record_type="A")

    # Migrate all zones in the project
    test_utils.call_migrate(
        test_config_path,
        [
            "start-batch",
            "--resource-type=dns-zone",
            "--include-dependencies",
            "--filter",
            f"project-id:{test_owner_source_project.id}",
            "--cleanup-source",
        ],
    )

    dest_zone = test_destination_session.dns.find_zone(zone.name)
    assert dest_zone, "couldn't find migrated zone"
    request.addfinalizer(
        lambda: test_destination_session.dns.delete_zone(
            dest_zone.id, ignore_missing=True
        )
    )

    _check_migrated_zone(zone, dest_zone)

    # Verify recordset was also migrated
    dest_recordsets = [
        rs
        for rs in test_destination_session.dns.recordsets(zone=dest_zone.id)
        if rs.type not in ["NS", "SOA"]
    ]
    assert len(dest_recordsets) >= 1, "recordset not migrated with zone"

    # Verify source zone was cleaned up or is being deleted (asynchronous)
    source_zone_after = test_source_session.dns.find_zone(zone.id, ignore_missing=True)
    if source_zone_after:
        assert getattr(source_zone_after, "action", "") == "DELETE", (
            "cleanup-source didn't trigger zone deletion"
        )
