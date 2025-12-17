Initiating migrations
=====================

Make sure to properly configure ``sunbeam-migrate`` before initiating resource
migrations. See the :ref:`tutorial <getting_started_ref>` and the
:ref:`configuration reference <config_ref>` to get started.

The :ref:`migration handlers page <migration_handlers_ref>` covers every
migratable resource type, including examples.

Migrating individual resources
------------------------------

The syntax for individual resource migrations is the following:

.. code-block:: none

  sunbeam-migrate start -h
  Usage: sunbeam-migrate start [OPTIONS] RESOURCE_ID

    Migrate an individual resource.

  Options:
    --resource-type TEXT    The migrated resource type (e.g. image, secret)
    --cleanup-source        Cleanup the resources on the source side if the
                            migration succeeds.
    --include-dependencies  Automatically migrate associated resources.
    --include-members       Automatically migrate member resources (contained
                            resources).
    -h, --help              Show this message and exit

At minimum, we need to specify the type of the resource to migrate and its ID
(a UUID in most cases).

See the :ref:`architecture page <resource_hierarchies_ref>` for an explanation
of how ``sunbeam-migrate`` handles resource dependencies.

If ``--cleanup-source`` is specified, successfully migrated resources are
automatically removed from the source cloud. This
:ref:`may also be done subsequently <cleaning_up_ref>`.

Batch migrations
----------------

``sunbeam-migrate`` can migrate a group of resources that match user
specified filters:

.. code-block:: none

  sunbeam-migrate start-batch -h
  Usage: sunbeam-migrate start-batch [OPTIONS]

    Migrate multiple resources that match the filters.

  Options:
    --resource-type TEXT    The migrated resource type (e.g. image, secret)
    --filter TEXT           One or more filters used to select the resources to
                            migrate.
    --dry-run               Only log the steps to be executed, skipping
                            migrations.
    --all                   Migrate all resources.
    --cleanup-source        Cleanup the resources on the source side if the
                            migration succeeds.
    --include-dependencies  Automatically migrate associated resources.
    --include-members       Automatically migrate member resources (contained
                            resources).
    -h, --help              Show this message and exit.

The ``--resource-type`` parameter is mandatory.

``--all`` will migrate all the resources belonging to the specified project.

Use the :doc:`capabilities <./capabilities>` command to see the list of
filters supported by each migration handler.

It's usually a good idea to do a dry run first using the ``--dry-run`` flag
to determine the resources that are going to be migrated.
