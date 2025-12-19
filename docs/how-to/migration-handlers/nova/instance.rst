Migrating instances
===================

``sunbeam-migrate`` can transfer Nova instances along with associated resources
such as:

* network resources

  * networks
  * subnets
  * ports

    * security groups

      * security group rules

    * floating IPs

* storage resources

  * instance root disk
  * Cinder volumes

* Nova specific resources

  * flavors
  * keypairs (if ``multi-tenant`` mode is disabled)

Instances that are booted from image will be temporarily uploaded to Glance
in order to transfer the root disk data.

The same applies to attached volumes, which will be migrated using temporary
Glance images.

Note that instance ports are created using the Neutron API in order to preserve
certain properties that are not exposed by Nova (e.g. port MAC address or
vNIC type). However, this means that Nova will not delete these ports when
the instance is destroyed.

The user can configure whether ``sunbeam-migrate`` should preserve the following:

* instance availability zone
* port fixed IP and MAC addresses
* floating IP, optionally using the exact same address
* network segmentation IDs
* volume type

.. note::

  If the desired networks and subnets and routers have been manually recreated
  on the destination side, make sure to import them in ``sunbeam-migrate`` using
  the ``register-external`` command.

Example
-------

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=instance \
    --include-dependencies \
    8a04813d-7942-475a-bba6-4d5b244dffa8

  2025-12-18 12:36:36,868 INFO Initiating instance migration, resource id: 8a04813d-7942-475a-bba6-4d5b244dffa8
  2025-12-18 12:36:39,220 WARNING Keypair migration is not supported in multi-tenant mode.
  2025-12-18 12:36:39,228 INFO Migrating associated project resource: 17a52ce3b69a44bdbaa054b54c511abc
  2025-12-18 12:36:39,229 INFO Initiating project migration, resource id: 17a52ce3b69a44bdbaa054b54c511abc
  2025-12-18 12:36:39,798 INFO Migrating associated domain resource: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 12:36:39,800 INFO Initiating domain migration, resource id: 38da677b7dd944f8bce50bba4342bda6
  2025-12-18 12:36:41,280 WARNING Domain already exists: 6f05f02ce89b4976bb6f06bce3d2a40a admin_domain
  2025-12-18 12:36:41,294 INFO Successfully migrated domain resource, destination id: 6f05f02ce89b4976bb6f06bce3d2a40a
  2025-12-18 12:36:43,368 WARNING Project already exists: cab1237c57b343d38ecff1423d82b8d2 test-1467433536-owner
  2025-12-18 12:36:43,373 INFO Successfully migrated project resource, destination id: cab1237c57b343d38ecff1423d82b8d2
  2025-12-18 12:36:43,382 INFO Migrating associated port resource: cd47bbc1-1437-412e-b1aa-3ea724675e19
  2025-12-18 12:36:43,385 INFO Initiating port migration, resource id: cd47bbc1-1437-412e-b1aa-3ea724675e19
  2025-12-18 12:36:44,241 INFO Migrating associated network resource: 7f392164-88a2-43d3-b39d-4f77f9d4dbb4
  2025-12-18 12:36:44,242 INFO Initiating network migration, resource id: 7f392164-88a2-43d3-b39d-4f77f9d4dbb4
  2025-12-18 12:36:47,958 INFO Successfully migrated network resource, destination id: 75f2806e-0e85-4af0-a580-27947a88754f
  2025-12-18 12:36:47,969 INFO Migrating associated subnet resource: 6c0b213a-585a-49d3-a5da-6e209d1a4c4d
  2025-12-18 12:36:47,971 INFO Initiating subnet migration, resource id: 6c0b213a-585a-49d3-a5da-6e209d1a4c4d
  2025-12-18 12:36:51,434 INFO Successfully migrated subnet resource, destination id: 2f28394b-7b11-40b3-8df9-aac14431a1b2
  2025-12-18 12:36:51,440 INFO Migrating associated security-group resource: 073320dc-732a-4a84-8548-214c0774831f
  2025-12-18 12:36:51,441 INFO Initiating security-group migration, resource id: 073320dc-732a-4a84-8548-214c0774831f
  2025-12-18 12:36:54,069 INFO Successfully migrated security-group resource, destination id: da071694-55e6-4402-93a6-0f853ad84e9a
  2025-12-18 12:36:57,404 INFO Successfully migrated port resource, destination id: d0e2b338-8c34-4959-952b-818abdfcaee9
  2025-12-18 12:36:57,414 INFO Migrating associated flavor resource: f128eb24-47ec-427a-a2a6-ccfbafce105f
  2025-12-18 12:36:57,415 INFO Initiating flavor migration, resource id: f128eb24-47ec-427a-a2a6-ccfbafce105f
  2025-12-18 12:37:01,436 WARNING Flavor already exists: 10f6b1f2-72e0-4d76-a245-0ae38d37d078 m1.xtiny
  2025-12-18 12:37:01,439 INFO Successfully migrated flavor resource, destination id: 10f6b1f2-72e0-4d76-a245-0ae38d37d078
  2025-12-18 12:37:03,801 WARNING Keypair migration is not supported in multi-tenant mode.
  2025-12-18 12:37:08,603 INFO Uploading instance 8a04813d-7942-475a-bba6-4d5b244dffa8 to image: instmigr-8a04813d-7942-475a-bba6-4d5b244dffa8-3260218961
  2025-12-18 12:37:09,918 INFO Waiting for instance upload to complete. Image id: 6729b935-3281-4575-83d0-6f99fb99a237
  2025-12-18 12:37:21,028 INFO Finished uploading instance to Glance.
  2025-12-18 12:37:21,062 INFO Initiating image migration, resource id: 6729b935-3281-4575-83d0-6f99fb99a237
  2025-12-18 12:37:25,699 INFO Successfully migrated image resource, destination id: a4580bc8-ac58-4eee-96fd-00459eeed369
  2025-12-18 12:37:25,704 INFO Migration succeeded, cleaning up source image: 6729b935-3281-4575-83d0-6f99fb99a237
  2025-12-18 12:37:31,434 INFO Waiting for instance provisioning: 12d3b2c0-82a0-4a08-b06f-acf6d975e523
  2025-12-18 12:37:50,942 INFO Deleting temporary image on source side: 6729b935-3281-4575-83d0-6f99fb99a237
  2025-12-18 12:37:50,975 INFO Deleting temporary image on destination side: a4580bc8-ac58-4eee-96fd-00459eeed369
  2025-12-18 12:37:52,982 INFO Successfully migrated instance resource, destination id: 12d3b2c0-82a0-4a08-b06f-acf6d975e523
