Migrating projects
==================


Roles would usually be migrated as user :ref:`dependencies<resource_hierarchies_ref>`.

If the deployments use non-standard role names, consider recreating the roles
manually and then use the ``register-external`` command so that the new users
will use the manually created roles.

Example
-------

The following example migrates an user and all the dependent resources:

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=role \
    --include-dependencies \
    b02b88f0855644bc9be5c5ea6f1b33da

  2025-12-18 15:23:39,306 INFO Initiating role migration, resource id: b02b88f0855644bc9be5c5ea6f1b33da
  2025-12-18 15:23:40,039 INFO Migrating associated domain resource: 86254561321249be94598fc4b8143669
  2025-12-18 15:23:40,041 INFO Initiating domain migration, resource id: 86254561321249be94598fc4b8143669
  2025-12-18 15:23:41,827 INFO Successfully migrated domain resource, destination id: 996f05c84596490fa3eb64b668e42621
  2025-12-18 15:23:43,967 INFO Successfully migrated role resource, destination id: 43f9763cd86b4e4fb5377d06e57ae1e7
