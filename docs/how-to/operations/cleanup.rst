.. _cleaning_up_ref:

Cleaning up migrated resources
==============================

Successfully migrated resources are automatically removed from the source cloud
if the ``--cleanup-source`` flag is provided. The operation can cascade
to :ref:`member resources <resource_hierarchies_ref>` and dependencies that
are not shared with other resources.

Alternatively, users may want to remove the original resources at a later time,
after validating the migrations on the destination cloud.

Use the ``cleanup-source`` command to do so:

.. code-block:: none

  sunbeam-migrate cleanup-source -h

  Usage: sunbeam-migrate cleanup-source [OPTIONS]

    Cleanup the source after successful migrations.

    Receives optional filters that specify which resources to clean up.

  Options:
    --service TEXT        Filter by service name
    --resource-type TEXT  Filter by resource type
    --source-id TEXT      Filter by source resource id.
    --all                 Cleanup all succeeded migrations.
    --dry-run             Dry run: only log the resources to be deleted.
    -h, --help            Show this message and exit.

The command receives various filters that will determine which migrated
resources should be cleaned up.
