Migrating security groups rules
===============================

Security group rules would usually be migrated as security group
:ref:`members <resource_hierarchies_ref>`. However, ``sunbeam-migrate``
also allows migrating individual rules. 

.. note::

  Security group rules may reference other security groups (via ``remote_group_id``).
  Consider migrating all security groups before recreating security group rules.
  One simple solution would be to perform a **security group batched migration**
  in two steps: one without ``--include-members`` and then another run with
  ``--include-members``.

We recommend using the ``--include-dependencies`` flag to also migrate the parent
security group as well as Keystone resources, if multi-tenant mode is enabled.

Example
-------

.. code-block:: none

  sunbeam-migrate start \
    --include-dependencies \
    --resource-type=security-group-rule \
    373c9707-b234-489b-a904-dd7e0f87a0c4

  2025-11-24 12:16:12,146 INFO Initiating security-group-rule migration, resource id: 373c9707-b234-489b-a904-dd7e0f87a0c4
  2025-11-24 12:16:17,934 INFO Successfully migrated resource, destination id: 194b1948-b29b-41d9-a5c9-152c3d5c9f5a
