# AI agent guidelines

## Overview

- `sunbeam-migrate` is a command-line tool that facilitates the migration of
  resources between OpenStack clouds (e.g. images, networks, volumes, etc.).
- The documentation under `docs/` provides usage examples.
- `sunbeam-migrate start` can be used to migrate a single resource, specifying
  the resource ID and resource type.
- `sunbeam-migrate start-batch` migrates all the resources that match a given set
  of filters.
- If the `--include-dependencies` flag is set, resource dependencies will be
  migrated automatically. For example, secrets referenced by a secret container
  or volumes attached to an instance.
- Similarly, the `--include-members` flag can be used to automatically migrate
  member (contained) resources, for example subnets of a network or security group
  rules belonging to a security group.
- The `--cleanup-source` flag can be used to automatically remove the resources
  on the source side if the migration succeeds.
- The `sunbeam-migrate list` command enumaretes the migrations, along with the
  resource type, source resource id, destination resource id and migration status.
- an environment variable called SUNBEAM_MIGRATE_CONFIG is used to provide a
  configuration file. Among other settings, it points to a clouds.yaml file that
  has credentials for the source and destination clouds.

## Architecture

- The tool is written in Python and should be Python 3.12 compatible.
- CLI commands are defined using the click framework and reside in the `cmd` folder.
- The migration information is stored in a Sqlite database, accessed using SQLAlchemy
  - Database operations are defined in db/api.py, the rest of the code should not
    use SQLAlchemy directly.
- The `handlers` folder contains resource migration handlers, grouped by service type.
  Format: `handlers/<service_name>/<resource_type>.py`.
- `handlers/base.py` defines the handler interface and includes common helper methods.
  - An OpenStack SDK session for the source cloud can be accessed throgh the 
    `_source_session` handler property. A similar property exists for the
    destination cloud.
- manager.py retrieves the right handler for a given resource type and orchestrates the
  migration.
  - The `get_migration_handler` factory function is used to obtain a migration
    handler.
- The resource handlers do not directly access DB models, only the manager does.
- The handlers use the OpenStack SDK to retrieve, create or delete OpenStack resources.
- Pydantic is used to define configuration options, which reside in config.py
- The manager calls the `get_associated_resources` handler method to obtain the list of
  dependent resources and migrates them before initating the requested migration.
  `perform_individual_migraiton` will receive a list of migrated resource objects
  via the `migrated_associated_resources` argument.
  - The migration handler can use the `_get_associated_resource_destination_id`
    helper to retrieve the corresponding id for a migrated dependency.

## Integration tests
  - `tests/integration` contains integration tests for each migration handler.
    File path format: `tests/integration/handlers/<service_name>/test_<resource_type>.py`
  - We're using the Pytest framework
  - conftest.py defines fixtures that create temporary OpenStack credentials
    and cleanup the resources at the end of the tests.
  - The test accepts a config file similar to the one used by sunbeam-migrate.
  - There are fixtures that return the test config path as well as OpenStack SDK
    sessions for both the source and destination clouds.
  - The tests should not use the `base_` fixtures directly, those are meant to
    set up the temporary credentials and configs.
  - Agents may use the existing tests as reference.
  - Pytest finalizers are used to remove test resources.
  - The integration tests use the temporary test credentials to create resources
    and then migrate them. Individual migrations receive the source resource IDs.
    - If multi-tenant mode is enabled, a separate set of credentials will be used
      to trigger the migration. This is transparently handled by the
      `test_requester_*` and `test_owner_*` fixtures.
  - The tests perform individual as well as batch migrations, often filtering
    resources by id or by the owner project and passing `--cleanup-source`.
  - If the migration handler does not support resource filters, batch migrations
    should be skipped by the tests.
  - The `get_destination_resource_id` test helper can be used to retrieve the id
    of the migrated resource, as reported by the destination cloud.

## Other rules

- AI agents should not generate unit or integration tests unless asked to.
- When modifying Markdown tables, the columns should be properly aligned.
- If an agent regenerates a file, avoid appending the new content, but instead
  replace the file contents. We don't want duplicate definitions.
- Empty __init__.py files should not contain license headers.
- Use Linux style line endings.
- All public methods should include docstrings. Subclasses may reuse the ones
  from the parent class.
- Agents should honor the ruff coding style rules as per tox.ini and
  pyproject.toml.
