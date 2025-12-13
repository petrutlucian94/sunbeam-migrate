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
def test_owner_project_name() -> str:
    # The project owning the migrated resources.
    return test_utils.get_test_resource_name()


@pytest.fixture(scope="module")
def test_requester_project_name(base_config, test_owner_project_name) -> str:
    # The project that requests the migrations.
    # If multi-tenant mode is disabled, it will be the
    # resource owner.
    if base_config.multitenant_mode:
        return test_utils.get_test_resource_name() + "-req"
    else:
        return test_owner_project_name


@pytest.fixture(scope="module")
def test_owner_user_name(test_owner_project_name) -> str:
    return test_owner_project_name


@pytest.fixture(scope="module")
def test_requester_user_name(test_requester_project_name) -> str:
    return test_requester_project_name


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
def test_owner_source_project(
    base_source_session,
    test_owner_project_name,
) -> Generator[sdk_project.Project]:
    LOG.info("Creating source owner test project: %s", test_owner_project_name)
    project = _create_test_project(base_source_session, test_owner_project_name)

    yield project

    LOG.info("Deleting source owner test project: %s", test_owner_project_name)
    base_source_session.identity.delete_project(project)


@pytest.fixture(scope="module")
def test_requester_source_project(
    base_config,
    base_source_session,
    test_requester_project_name,
    test_owner_source_project,
) -> Generator[sdk_project.Project]:
    # TODO: use a separate domain.
    if base_config.multitenant_mode:
        LOG.info(
            "Creating source requester test project: %s", test_requester_project_name
        )
        project = _create_test_project(base_source_session, test_requester_project_name)

        yield project

        LOG.info(
            "Deleting source requester test project: %s", test_requester_project_name
        )
        base_source_session.identity.delete_project(project)
    else:
        yield test_owner_source_project


@pytest.fixture(scope="module")
def test_owner_destination_project(
    base_config,
    base_destination_session,
    test_owner_project_name,
) -> Generator[sdk_project.Project]:
    LOG.info("Creating destination owner test project: %s", test_owner_project_name)
    project = _create_test_project(base_destination_session, test_owner_project_name)

    yield project

    LOG.info("Deleting destination owner test project: %s", test_owner_project_name)
    base_destination_session.identity.delete_project(project)


@pytest.fixture(scope="module")
def test_requester_destination_project(
    base_config,
    base_destination_session,
    test_requester_project_name,
    test_owner_destination_project,
) -> Generator[sdk_project.Project]:
    if base_config.multitenant_mode:
        LOG.info(
            "Creating destination requester test project: %s",
            test_requester_project_name,
        )
        project = _create_test_project(
            base_destination_session, test_requester_project_name
        )

        yield project

        LOG.info(
            "Deleting destination requester test project: %s",
            test_requester_project_name,
        )
        base_destination_session.identity.delete_project(project)
    else:
        yield test_owner_destination_project


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
def test_owner_source_user(
    base_config,
    base_source_session,
    test_owner_source_project,
    test_owner_user_name,
    test_user_roles,
    test_source_session,
) -> Generator[sdk_user.User]:
    LOG.info(
        "Creating source test user: %s, roles: %s",
        test_owner_user_name,
        test_user_roles,
    )

    user = _create_test_user(
        base_source_session,
        test_owner_source_project,
        test_owner_user_name,
        test_user_roles,
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
def test_requester_source_user(
    base_config,
    base_source_session,
    test_requester_source_project,
    test_owner_source_user,
    test_requester_user_name,
    test_user_roles,
    test_source_session,
) -> Generator[sdk_user.User]:
    if base_config.multitenant_mode:
        LOG.info(
            "Creating source requester test user: %s, roles: %s",
            test_requester_user_name,
            test_user_roles,
        )

        user = _create_test_user(
            base_source_session,
            test_requester_source_project,
            test_requester_user_name,
            test_user_roles,
        )

        yield user

        # The requester user is not expected to own any resources, as such we'll
        # skip the project purge operation, which is time consuming (~30s).
        LOG.info("Deleting requester source user: %s", user.name)
        base_source_session.identity.delete_user(user)
    else:
        yield test_owner_source_user


@pytest.fixture(scope="module")
def test_owner_destination_user(
    base_config,
    base_destination_session,
    test_owner_destination_project,
    test_owner_user_name,
    test_user_roles,
    test_destination_session,
) -> Generator[sdk_user.User]:
    LOG.info(
        "Creating destination test user: %s, roles: %s",
        test_owner_user_name,
        test_user_roles,
    )
    user = _create_test_user(
        base_destination_session,
        test_owner_destination_project,
        test_owner_user_name,
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
def test_requester_destination_user(
    base_config,
    base_destination_session,
    test_requester_destination_project,
    test_requester_user_name,
    test_user_roles,
    test_destination_session,
) -> Generator[sdk_user.User]:
    LOG.info(
        "Creating destination requester test user: %s, roles: %s",
        test_requester_user_name,
        test_user_roles,
    )
    user = _create_test_user(
        base_destination_session,
        test_requester_destination_project,
        test_requester_user_name,
        test_user_roles,
    )

    yield user

    LOG.info("Deleting destination user: %s", user.name)
    base_destination_session.identity.delete_user(user)


@pytest.fixture(scope="module")
def test_config_path(tmpdir_factory) -> Path:
    """The sunbeam-migrate config used for this class of tests."""
    return Path(
        tmpdir_factory.mktemp("sunbeam_migrate").join("sunbeam-migrate-config.yaml")
    )


@pytest.fixture(scope="module")
def test_owner_cloud_config_path(tmpdir_factory) -> Path:
    """The Openstack clouds.yaml used for this class of tests."""
    return Path(tmpdir_factory.mktemp("sunbeam_migrate").join("clouds-owner.yaml"))


@pytest.fixture(scope="module")
def test_requester_cloud_config_path(tmpdir_factory) -> Path:
    """The Openstack clouds.yaml used for this class of tests."""
    return Path(tmpdir_factory.mktemp("sunbeam_migrate").join("clouds-requester.yaml"))


@pytest.fixture(scope="module")
def test_database_path(tmpdir_factory) -> Path:
    """The Openstack clouds.yaml used for this class of tests."""
    return Path(tmpdir_factory.mktemp("sunbeam_migrate").join("sqlite.db"))


def _prepare_cloud_config(
    base_config: config.SunbeamMigrateConfig,
    project_name: str,
    user_name: str,
    output_path: Path,
):
    assert base_config.cloud_config_file
    with base_config.cloud_config_file.open() as f:
        cloud_config = yaml.safe_load(f)

    clouds_section = cloud_config["clouds"]
    source_auth = clouds_section[base_config.source_cloud_name]["auth"]
    destination_auth = clouds_section[base_config.destination_cloud_name]["auth"]

    source_auth["project_name"] = project_name
    source_auth["username"] = user_name
    source_auth["password"] = TEST_USER_PASSWORD
    destination_auth["project_name"] = project_name
    destination_auth["username"] = user_name
    destination_auth["password"] = TEST_USER_PASSWORD

    with output_path.open("w") as f:
        f.write(yaml.dump(cloud_config))


@pytest.fixture(scope="module")
def test_requester_cloud_config(
    base_config,
    test_requester_project_name,
    test_requester_user_name,
    test_requester_cloud_config_path,
):
    LOG.info("Preparing requester clouds.yaml: %s", test_requester_cloud_config_path)
    _prepare_cloud_config(
        base_config,
        test_requester_project_name,
        test_requester_user_name,
        test_requester_cloud_config_path,
    )


@pytest.fixture(scope="module")
def test_owner_cloud_config(
    base_config,
    test_owner_project_name,
    test_owner_user_name,
    test_owner_cloud_config_path,
):
    LOG.info("Preparing owner clouds.yaml: %s", test_owner_cloud_config_path)
    _prepare_cloud_config(
        base_config,
        test_owner_project_name,
        test_owner_user_name,
        test_owner_cloud_config_path,
    )


@pytest.fixture(scope="module")
def test_config(
    base_config,
    test_config_path,
    test_requester_cloud_config_path,
    test_database_path,
    test_requester_cloud_config,
) -> config.SunbeamMigrateConfig:
    LOG.info("Preparing sunbeam-migrate config: %s", test_config_path)
    conf = config.SunbeamMigrateConfig(**base_config.model_dump())
    conf.database_file = test_database_path
    conf.cloud_config_file = test_requester_cloud_config_path

    with test_config_path.open("w") as f:
        dump = json.loads(conf.model_dump_json())
        f.write(yaml.dump(dump))

    return conf


@pytest.fixture(scope="module")
def test_owner_source_session(
    base_config,
    test_owner_cloud_config_path,
    test_owner_cloud_config,
):
    return test_utils.get_openstack_session(
        test_owner_cloud_config_path, base_config.source_cloud_name
    )


@pytest.fixture(scope="module")
def test_requester_source_session(
    base_config,
    test_owner_cloud_config_path,
):
    return test_utils.get_openstack_session(
        test_requester_cloud_config_path, base_config.source_cloud_name
    )


@pytest.fixture(scope="module")
def test_owner_destination_session(
    test_config,
    test_owner_cloud_config_path,
):
    return test_utils.get_openstack_session(
        test_owner_cloud_config_path, test_config.destination_cloud_name
    )


@pytest.fixture(scope="module")
def test_requester_destination_session(
    test_config,
    test_requester_cloud_config_path,
):
    return test_utils.get_openstack_session(
        test_requester_cloud_config_path, test_config.destination_cloud_name
    )


@pytest.fixture(scope="module")
def test_source_session(test_owner_source_session):
    yield test_owner_source_session


@pytest.fixture(scope="module")
def test_destination_session(test_owner_destination_session):
    yield test_owner_destination_session


@pytest.fixture(scope="module")
def test_credentials(
    test_owner_source_user,
    test_owner_destination_user,
    test_requester_source_user,
    test_requester_destination_user,
):
    """Create temporary credentials on both clouds."""
    pass
