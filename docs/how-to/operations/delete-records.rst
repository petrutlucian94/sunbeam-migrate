.. _delete-records-ref:

Deleting migration records
--------------------------

Users can remove migration records from the ``sunbeam-migrate`` database
using the following command:

.. code-block:: none

  sunbeam-migrate delete -h
  Usage: sunbeam-migrate delete [OPTIONS]

    Remove migrations from the sunbeam-migrate database.

    Receives optional filters that are joined using "AND" logical operators.
    Performs a soft deletion unless "--hard" is specified.

  Options:
    --service TEXT        Filter by service name
    --resource-type TEXT  Filter by resource type
    --id TEXT             Filter by migration id.
    --status TEXT         Filter by migration status.
    --source-id TEXT      Filter by source resource id.
    --archived            Delete archived migrations.
    --hard                Perform hard deletion.
    --all                 Delete all migrations.
    -h, --help            Show this message and exit.

This can be useful if the migration database gets exceedingly large or if there
are unwanted records (e.g. failures that have been resolved in the meantime).

It also allows already completed migrations to be repeated, for example if the
destination resource was deleted.

The command receives a set of filters that determine which migration records
will be removed. By default, the entries are soft deleted and
:ref:`can be restored<restore-records-ref>`.
