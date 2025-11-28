# AI agent guidelines

## Overview

- "sunbeam-migrate" is a command-line tool that facilitates the migration of
  resources between OpenStack clouds (e.g. images, networks, volumes, etc.).
- README.md provides a few usage examples.
- "sunbeam-migrate start" can be used to migrate a single resource, specifying
  the resource ID and resource type.
- "sunbeam-migrate start-batch" migrates all the resources that match a given set
  of filters.
- If the "--include-dependencies" flag is set, resource dependencies will be
  migrated automatically. For example, secrets referenced by a secret container
  or volumes attached to an instance.
- Similarly, the "--include-members" flag can be used to automatically migrate
  member (contained) resources, for example subnets of a network or security group
  rules belonging to a security group.
- The "--cleanup-source" flag can be used to automatically remove the resources
  on the source side if the migration succeeds.
- The "sunbeam-migrate list" command enumaretes the migrations, along with the
  resource type, source resource id, destination resource id and migration status.
- an environment variable called SUNBEAM_MIGRATE_CONFIG is used to provide a
  configuration file. Among other settings, it points to a clouds.yaml file that
  has credentials for the source and destination clouds.

## Architecture

- The tool is written in Python and should be Python 3.12 compatible.
- CLI commands are defined using the click framework and reside in the "cmd" folder.
- The migration information is stored in a Sqlite database, accessed using SQLAlchemy
  - Database operations are defined in db/api.py, the rest of the code should not
    use SQLAlchemy directly.
- The "handlers" folder contains resource migration handlers, grouped by service type.
  Format: "handlers/<service_name>/<resource_type>.py".
- handlers/base.py defines the handler interface and includes common helper methods.
  - An openstack sdk session for the source cloud can be accessed throgh the 
    "_source_session" handler property. A similar property exists for the
    destination cloud.
- manager.py retrieves the right handler for a given resource type and orchestrates the
  migration.
- The resource handles do not directly access DB models, only the manager does.
- The handlers use the OpenStack SDK to retrieve or create Openstack resources.
- Pydantic is used to define configuration options, which reside in config.py
- The manager uses the "get_associated_resources" handler method to obtain the list of
  dependent resources and migrates them before initating the requested migration.
  "perform_individual_migraiton" will receive a list of migrated resource tuples
  via the "migrated_associated_resources" argument.
  - The migration handler can use the "_get_associated_resource_destination_id"
    helper to retrieve the corresponding id for a migrated dependency.
  - For example, if an instance needs volume "source-volume-id", the
   "migrated_associated_resources" argument will look like this:
   [("volume", "source-volume-id", "destination-volume-id")],
   where "destination-volume-id" is the uuid of the migrated volume reported by the
   destination cloud.

## Other rules

- AI agents should not generate unit or integration tests yet unless asked to.
- When modifying markdown tables, the columns should be properly aligned.
- If an agent regenerates a file, avoid appending the new content, but instead replace
  the file contents. We don't want duplicate definitions.
- Empty __init__.py files should not contain license headers.
- Use Linux style line endings.
- All public methods should include docstrings. Subclasses may reuse the ones
  from the parent class.
- Agents should honor the ruff coding style rules as per tox.ini and
  pyproject.toml.
