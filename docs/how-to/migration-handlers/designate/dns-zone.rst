Migrating DNS zones and records
-------------------------------

Designate zones can be migrated with `--resource-type=dns-zone`. The handler
recreates the DNS zone with all of its recordsets on the destination.

.. note::

  Consider passing ``--include-dependencies`` if the multi-tenant mode
  is enabled in order to automatically recreate the Keystone resources.

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=dns-zone \
    68cfff5c-02dd-44b6-a436-b87d82f2a1d6

  2025-12-15 15:42:58,313 INFO Initiating dns-zone migration, resource id: 68cfff5c-02dd-44b6-a436-b87d82f2a1d6
  2025-12-15 15:43:11,744 INFO Creating zone test.example.com. on destination
  2025-12-15 15:43:12,883 INFO Created zone test.example.com. on destination (id: d8e32ae7-1363-4900-98a1-abb0409884e4)
  2025-12-15 15:43:12,884 INFO Copying recordsets from source zone 68cfff5c-02dd-44b6-a436-b87d82f2a1d6 to destination zone d8e32ae7-1363-4900-98a1-abb0409884e4
  2025-12-15 15:43:13,219 INFO Copying recordset: note.test.example.com. (TXT)
  2025-12-15 15:43:14,656 INFO Created recordset: note.test.example.com. (TXT)
  2025-12-15 15:43:14,688 INFO Successfully migrated dns-zone resource, destination id: d8e32ae7-1363-4900-98a1-abb0409884e4