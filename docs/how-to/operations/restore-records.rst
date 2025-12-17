.. _restore-records-ref:

Restoring migration records
---------------------------

Soft-deleted migration records can be restored using the following command:

.. code-block:: none

  sunbeam-migrate restore -h
  Usage: sunbeam-migrate restore [OPTIONS]

    Restore soft-deleted migrations.

    Receives optional filters that are joined using "AND" logical operators.

  Options:
    --service TEXT        Filter by service name
    --resource-type TEXT  Filter by resource type
    --id TEXT             Filter by migration id.
    --status TEXT         Filter by migration status.
    --source-id TEXT      Filter by source resource id.
    -h, --help            Show this message and exit.

Similarly to the :ref:`delete command<delete-records-ref>`, it receives a set
of filters.
