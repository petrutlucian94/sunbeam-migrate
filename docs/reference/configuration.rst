.. _config_ref:

Configuration
=============

``sunbeam-migrate`` receives a YAML configuration file that defines:

* the source and destination cloud
* credentials used to identify and migrate resources
* internal Sqlite database location
* timeouts
* whether to preserve certain resource properties (e.g. volume types,
  availability zones, network segmentation IDs, MAC addresses, etc)
* multi-tenant mode

The location of this file can be specified either using the
``SUNBEAM_MIGRATE_CONFIG`` environment variable or through the ``--config``
parameter.

Minimal sample
--------------

.. code-block:: yaml

  log_level: info
  cloud_config_file: /home/ubuntu/cloud-config.yaml
  source_cloud_name: source-admin
  destination_cloud_name: destination-admin
  database_file: /home/ubuntu/.local/share/sunbeam-migrate/sqlite.db
  multitenant_mode: true

``cloud_config_file`` is a standard OpenStack `clouds yaml`_ file that contains
Openstack credentials for the source and destination clouds. Here is an example:

.. code-block:: yaml

  clouds:
    source-admin:
      auth:
        auth_url: https://public.source.local/openstack-keystone/v3
        password: pwned
        project_domain_name: admin_domain
        project_name: admin
        user_domain_name: admin_domain
        username: admin
      cacert: /home/ubuntu/sunbeam-ca/sunbeam-source-ca.pem
    destination-admin:
      auth:
        auth_url: https://public.destination.local/openstack-keystone/v3
        password: pwned
        project_domain_name: admin_domain
        project_name: admin
        user_domain_name: admin_domain
        username: admin
      cacert: /home/ubuntu/sunbeam-ca/sunbeam-destination-ca.pem

Cloud configurations
--------------------

We are uploading the Cinder volumes to Glance in order to retrieve the data.
On the source cloud, Cinder must be configured with `enable_force_upload = True`
in order to upload attached volumes.

As we are uploading the Cinder volumes and Nova instance root disks to Glance,
the Glance services on both clouds must have the `image_size_cap` config option
set to a high enough value to accommodate these migrations (default value: 1 TB).

Options
-------

This section describes each of the available options.

``log_level``
~~~~~~~~~~~~~

| **Type:** ``string``
| **Values:** ``debug``, ``info``, ``warning``, ``error``
| **Default:** ``info``
| **Description:** Defines the log level.

``log_dir``
~~~~~~~~~~~

| **Type:** ``string``
| **Default:** ``null``
| **Description:** Log directory (optional). If set, a new log file will be created at the specified location for each ``sunbeam-migrate`` invocation. Log files have the following format:
| ``sunbeam-migrate-%Y%m%d-%H%M%S.%f.log``.

``log_console``
~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``true``
| **Description:** Whether to use console logging.

``cloud_config_file``
~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``string``
| **Default:** ``null``
| **Description:** The Openstack cloud config file to use, expected to contain credentials for both the source and the destination clouds. See the `clouds yaml`_ documentation for more details.

``source_cloud_name``
~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``string``
| **Default:** ``null``
| **Description:** The name of the source cloud, as defined in the clouds file.

``destination_cloud_name``
~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``string``
| **Default:** ``null``
| **Description:** The name of the destination cloud, as defined in the clouds file.

``database_file``
~~~~~~~~~~~~~~~~~

| **Type:** ``string``
| **Default:** ``$HOME/.local/share/sunbeam-migrate/sqlite.db``
| **Description:** The internal Sqlite database location. ``sunbeam-migrate`` will create the directory automatically if missing.


``temporary_migration_dir``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``string``
| **Default:** ``$HOME/.local/share/sunbeam-migrate/migration_dir``
| **Description:** # The directory used to store temporary files and mounts used as part of the migration process.

``multitenant_mode``
~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``true``
| **Description:** The multi-tenant mode allows identifying and migrating resources owned by another tenant. This requires admin privileges. Identity resources such as domains, projects, users and roles will be treated as dependencies and migrated automatically if ``--include-dependencies`` is set.

``image_transfer_chunk_size``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``integer``
| **Default:** ``33554432 (32MB)``
| **Description:** The chunk size in bytes used when retrieving and uploading Glance images. These chunks are kept entirely in memory.

``volume_upload_timeout``
~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``integer``
| **Default:** ``1800 (30 minutes)``
| **Description:** How long to wait for Cinder volume uploads (seconds).

``resource_creation_timeout``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``integer``
| **Default:** ``300 (5 minutes)``
| **Description:** How long to wait for Openstack resources to be provisioned (seconds).

``preserve_volume_type``
~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``false``
| **Description:** Preserve the volume type when migrating volumes. Defaults to ``false`` for increased compatibility. If enabled, the volume types will be migrated and used when transferring volumes. Manually created types may be registered using the ``register-external`` command.

``preserve_volume_availability_zone``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``false``
| **Description:** Preserve the volume availability zone.

``preserve_instance_availability_zone``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``false``
| **Description:** Preserve the instance availability zone.

``preserve_load_balancer_availability_zone``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``false``
| **Description:** Preserve the load balancer availability zone.

``preserve_share_type``
~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``false``
| **Description:** Preserve the Manila share type.

``preserve_network_segmentation_id``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``false``
| **Description:** Preserve the network segmentation ID (e.g. VLAN tag or tunnel VNI). This is disabled by default since it may conflict with other existing networks from the destination cloud.

``preserve_port_mac_address``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``false``
| **Description:** Preserve Neutron port MAC addresses.

``preserve_port_floating_ip``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``false``
| **Description:** Preserve Neutron port floating IP.

``preserve_port_floating_ip_address``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``true``
| **Description:** Use the same IP address when migrating floating IPs. Consider disabling this when using a different public subnet on the destination cloud.

``preserve_port_fixed_ips``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``true``
| **Description:** Preserve the fixed IPs when migrating Neutron ports.

``preserve_router_ip``
~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``boolean``
| **Default:** ``true``
| **Description:** Use the same router IP.

``manila_local_access_ip``
~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Type:** ``string``
| **Default:** ``null``
| **Description:** The local IP address used to access Manila shares.

If unspecified, it will be automatically determined based on the host routes. When migrating shares, ``sunbeam-migrate`` transparently handles shares access rules in order to be able to mount the shares and transfer data.

``member_role_name``
~~~~~~~~~~~~~~~~~~~~

| **Type:** ``string``
| **Default:** ``member``
| **Description:** The name of the "member" Keystone role.

When migrating certain resources to other tenants (e.g. instances, volumes or shares), we need to a project scoped session using the destination project.

``sunbeam-migrate`` will transparently assign the member role to the user that initiated the migration.
