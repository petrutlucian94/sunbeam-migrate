# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml
from openstack.identity.v3 import project as sdk_project
from openstack.identity.v3 import user as sdk_user

from sunbeam_migrate import config
from sunbeam_migrate.tests.integration import config as integration_test_config
from sunbeam_migrate.tests.integration import utils as test_utils

LOG = logging.getLogger()

TEST_USER_PASSWORD = "test-user-password"


@pytest.fixture(scope="session")
def base_config_path() -> Path:
    # Admin config used to set up test resources.
    # The tests are expected to use temporary credentials and separate
    # configs.
    config_path = os.getenv("SUNBEAM_MIGRATE_CONFIG")
    assert config_path, "SUNBEAM_MIGRATE_CONFIG env variable missing."
    return Path(config_path)


@pytest.fixture(scope="session", autouse=True)
def base_config(base_config_path) -> integration_test_config.SunbeamMigrateTestConfig:
    conf = integration_test_config.SunbeamMigrateTestConfig()
    conf.load_config(base_config_path)
    return conf


@pytest.fixture(scope="session")
def base_source_session(base_config):
    assert base_config.source_cloud_name, "No source cloud specified."
    return test_utils.get_openstack_session(
        base_config.cloud_config_file, base_config.source_cloud_name
    )


@pytest.fixture(scope="session")
def base_destination_session(base_config):
    assert base_config.destination_cloud_name, "No destination cloud specified."
    return test_utils.get_openstack_session(
        base_config.cloud_config_file, base_config.destination_cloud_name
    )


@pytest.fixture(scope="module")
def test_project_name() -> str:
    return test_utils.get_test_resource_name()


@pytest.fixture(scope="module")
def test_user_name(test_project_name) -> str:
    return test_project_name


@pytest.fixture(scope="module")
def test_user_roles() -> list[str]:
    # TODO: this should be configurable.
    return ["member", "admin"]


def _get_domain_id(session, auth_field: str = "project_domain_name") -> str | None:
    domain_name = session.auth.get(auth_field)
    domain_id = None
    if domain_name:
        domain = session.identity.find_domain(domain_name, ignore_missing=False)
        domain_id = domain.id
    return domain_id


def _create_test_project(session, name) -> sdk_project.Project:
    return session.identity.create_project(
        name=name,
        description="sunbeam-migrate test project",
        domain_id=_get_domain_id(session, "project_domain_name"),
    )


@pytest.fixture(scope="module")
def test_source_project(
    base_source_session,
    test_project_name,
) -> Generator[sdk_project.Project]:
    LOG.info("Creating source test project: %s", test_project_name)
    project = _create_test_project(base_source_session, test_project_name)

    yield project

    LOG.info("Deleting source test project: %s", test_project_name)
    base_source_session.identity.delete_project(project)


@pytest.fixture(scope="module")
def test_destination_project(
    base_destination_session,
    test_project_name,
) -> Generator[sdk_project.Project]:
    LOG.info("Creating destination test project: %s", test_project_name)
    project = _create_test_project(base_destination_session, test_project_name)

    yield project

    LOG.info("Deleting destination test project: %s", test_project_name)
    base_destination_session.identity.delete_project(project)


def _create_test_user(session, project, user_name, roles) -> sdk_user.User:
    user = session.identity.create_user(
        name=user_name,
        default_project_id=project.id,
        description="sunbeam-migrate test user",
        password=TEST_USER_PASSWORD,
        domain_id=_get_domain_id(session, "user_domain_name"),
    )
    for role_name in roles:
        role = session.identity.find_role(role_name, ignore_missing=False)
        session.identity.assign_project_role_to_user(project, user, role)
    return user


@pytest.fixture(scope="module")
def test_source_user(
    base_config,
    base_source_session,
    test_source_project,
    test_user_name,
    test_user_roles,
    test_source_session,
) -> Generator[sdk_user.User]:
    LOG.info(
        "Creating source test user: %s, roles: %s", test_user_name, test_user_roles
    )

    user = _create_test_user(
        base_source_session, test_source_project, test_user_name, test_user_roles
    )

    yield user

    source_project_name = test_source_session.auth.get("project_name")
    if not base_config.skip_project_purge:
        LOG.info("Purging source project: %s", source_project_name)
        test_source_session.project_cleanup()
    else:
        LOG.info("Skipped purging source project: %s", source_project_name)

    LOG.info("Deleting source user: %s", user.name)
    base_source_session.identity.delete_user(user)


@pytest.fixture(scope="module")
def test_destination_user(
    base_config,
    base_destination_session,
    test_destination_project,
    test_user_name,
    test_user_roles,
    test_destination_session,
) -> Generator[sdk_user.User]:
    LOG.info(
        "Creating destination test user: %s, roles: %s", test_user_name, test_user_roles
    )
    user = _create_test_user(
        base_destination_session,
        test_destination_project,
        test_user_name,
        test_user_roles,
    )

    yield user

    destination_project_name = test_destination_session.auth.get("project_name")
    if not base_config.skip_project_purge:
        LOG.info("Purging destination project: %s", destination_project_name)
        test_destination_session.project_cleanup()
    else:
        LOG.info("Skipped purging destination project: %s", destination_project_name)

    LOG.info("Deleting destination user: %s", user.name)
    base_destination_session.identity.delete_user(user)


@pytest.fixture(scope="module")
def test_config_path(tmpdir_factory) -> Path:
    """The sunbeam-migrate config used for this class of tests."""
    return Path(
        tmpdir_factory.mktemp("sunbeam_migrate").join("sunbeam-migrate-config.yaml")
    )


@pytest.fixture(scope="module")
def test_cloud_config_path(tmpdir_factory) -> Path:
    """The Openstack clouds.yaml used for this class of tests."""
    return Path(tmpdir_factory.mktemp("sunbeam_migrate").join("clouds.yaml"))


@pytest.fixture(scope="module")
def test_database_path(tmpdir_factory) -> Path:
    """The Openstack clouds.yaml used for this class of tests."""
    return Path(tmpdir_factory.mktemp("sunbeam_migrate").join("sqlite.db"))


@pytest.fixture(scope="module")
def test_config(
    base_config,
    test_config_path,
    test_cloud_config_path,
    test_database_path,
    test_project_name,
    test_user_name,
) -> config.SunbeamMigrateConfig:
    conf = config.SunbeamMigrateConfig(**base_config.model_dump())
    conf.database_file = test_database_path
    conf.cloud_config_file = test_cloud_config_path

    with open(base_config.cloud_config_file) as f:
        cloud_config = yaml.safe_load(f)

    clouds_section = cloud_config["clouds"]
    source_auth = clouds_section[base_config.source_cloud_name]["auth"]
    destination_auth = clouds_section[base_config.destination_cloud_name]["auth"]

    source_auth["project_name"] = test_project_name
    source_auth["username"] = test_user_name
    source_auth["password"] = TEST_USER_PASSWORD
    destination_auth["project_name"] = test_project_name
    destination_auth["username"] = test_user_name
    destination_auth["password"] = TEST_USER_PASSWORD

    assert conf.cloud_config_file

    with conf.cloud_config_file.open("w") as f:
        f.write(yaml.dump(cloud_config))

    with test_config_path.open("w") as f:
        dump = json.loads(conf.model_dump_json())
        f.write(yaml.dump(dump))

    LOG.info("Prepared test config: %s", test_config_path)
    return conf


@pytest.fixture(scope="module")
def test_source_session(
    test_config,
    test_cloud_config_path,
):
    return test_utils.get_openstack_session(
        test_cloud_config_path, test_config.source_cloud_name
    )


@pytest.fixture(scope="module")
def test_destination_session(
    test_config,
    test_cloud_config_path,
):
    return test_utils.get_openstack_session(
        test_cloud_config_path, test_config.destination_cloud_name
    )


@pytest.fixture(scope="module")
def test_credentials(
    test_source_user,
    test_destination_user,
):
    """Create temporary credentials on both clouds."""
    pass
