Retrieving migration handler capabilities
-----------------------------------------

Run the following command to see the list of migration handlers, how they
define resource relations and which batch migration filters they accept:

.. code-block:: none

  sunbeam-migrate capabilities

  +-------------------------------------------------------------------------------------------------------------------------------------------+
  |                                                             Migration handlers                                                            |
  +-----------+---------------------+-----------------------+--------------------------------------------------------+------------------------+
  |  Service  |    Resource type    | Member resource types |               Associated resource types                | Batch resource filters |
  +-----------+---------------------+-----------------------+--------------------------------------------------------+------------------------+
  |  Barbican |        secret       |           -           |                           -                            |           -            |
  |  Barbican |   secret-container  |           -           |                         secret                         |           -            |
  |   Cinder  |        volume       |           -           |               volume-type, project, user               |       project_id       |
  |   Cinder  |     volume-type     |           -           |                           -                            |           -            |
  | Designate |       dns-zone      |           -           |                        project                         |       project_id       |
  |   Glance  |        image        |           -           |                        project                         |       project_id       |
  |  Keystone |        domain       |     project, user     |                           -                            |           -            |
  |  Keystone |       project       |          user         |                         domain                         |       domain_id        |
  |  Keystone |         role        |           -           |                         domain                         |       domain_id        |
  |  Keystone |         user        |           -           |                 domain, project, role                  |       domain_id        |
  |   Manila  |        share        |           -           |                  share-type, project                   |       project_id       |
  |   Manila  |      share-type     |           -           |                           -                            |           -            |
  |  Neutron  |     floating-ip     |           -           |            network, subnet, router, project            |       project_id       |
  |  Neutron  |       network       |         subnet        |                        project                         |       project_id       |
  |  Neutron  |         port        |           -           | network, subnet, security-group, floating-ip, project  |           -            |
  |  Neutron  |        router       |         subnet        |                network, subnet, project                |       project_id       |
  |  Neutron  |    security-group   |  security-group-rule  |                        project                         |       project_id       |
  |  Neutron  | security-group-rule |           -           |                security-group, project                 |       project_id       |
  |  Neutron  |        subnet       |           -           |                    network, project                    |       project_id       |
  |    Nova   |        flavor       |           -           |                           -                            |           -            |
  |    Nova   |       instance      |           -           | image, volume, flavor, keypair, network, port, project |       project_id       |
  |    Nova   |       keypair       |           -           |                           -                            |           -            |
  |  Octavia  |    load-balancer    |           -           |         network, subnet, floating-ip, project          |       project_id       |
  +-----------+---------------------+-----------------------+--------------------------------------------------------+------------------------+

We can also specify the resource type like so:

.. code-block:: none

  sunbeam-migrate capabilities --resource-type=instance

  +------------------------------------------------------------------------------------+
  |                                 Migration handler                                  |
  +---------------------------+--------------------------------------------------------+
  |          Property         |                         Value                          |
  +---------------------------+--------------------------------------------------------+
  |          Service          |                          Nova                          |
  |       Resource type       |                        instance                        |
  |   Member resource types   |                           -                            |
  | Associated resource types | image, volume, flavor, keypair, network, port, project |
  |   Batch resource filters  |                       project_id                       |
  +---------------------------+--------------------------------------------------------+
