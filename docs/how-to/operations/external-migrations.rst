Registering external migrations
-------------------------------

``sunbeam-migrate`` normally creates exact copies of the migrated resources.
This isn't always desired.

Let's take volume types for example. The extra specs may contain backend
specific properties that are not applicable on the destination cloud
(e.g. backend name, pool name or other storage backend settings).

Users can recreate the volume type manually on the destination cloud and then
use the ``register-external`` command to register the migration. It
receives the resource type along with the source and destination resource
IDs.

Subsequent volume migrations will automatically use the manually created volume type.

.. code-block:: none

  sunbeam-migrate register-external \
    --resource-type volume-type \
    f104d538-a2f0-4897-92ea-9887bfb1c926 \
    491481cd-d9d0-4639-afe4-d5f07223f4db

  sunbeam-migrate show fd91c637-7b91-4fb6-9bd6-afb84c9d79a1

  +----------------------------------------------------------+
  |                        Migration                         |
  +-------------------+--------------------------------------+
  |       Field       |                Value                 |
  +-------------------+--------------------------------------+
  |        Uuid       | fd91c637-7b91-4fb6-9bd6-afb84c9d79a1 |
  |     Created at    |      2025-12-02 10:44:22.062347      |
  |     Updated at    |                 None                 |
  |      Service      |                cinder                |
  |   Resource type   |             volume-type              |
  |    Source cloud   |             source-admin             |
  | Destination cloud |          destination-admin           |
  |     Source id     | f104d538-a2f0-4897-92ea-9887bfb1c926 |
  |   Destination id  | 491481cd-d9d0-4639-afe4-d5f07223f4db |
  |       Status      |              completed               |
  |   Error message   |                 None                 |
  |      Archived     |                False                 |
  |   Source removed  |                False                 |
  |      External     |                 True                 |
  +-------------------+--------------------------------------+
