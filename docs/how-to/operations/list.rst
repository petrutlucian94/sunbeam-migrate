Listing migrations
------------------

Use the following command to list the performed migrations:

.. code-block:: none

  sunbeam-migrate list

  +-----------------------------------------------------------------------------------------------------------------------------------------------------------+
  |                                                                         Migrations                                                                        |
  +--------------------------------------+----------+---------------+-----------+--------------------------------------+--------------------------------------+
  |                 UUID                 | Service  | Resource type |   Status  |              Source ID               |            Destination ID            |
  +--------------------------------------+----------+---------------+-----------+--------------------------------------+--------------------------------------+
  | 0209b968-10ae-4770-ac6e-6c454fb4323f |  glance  |     image     | completed | 5f7f24cc-b700-4195-80af-50e61adff91d | e1a526cf-1ac5-4532-a5f8-1069ea585c22 |
  | 3928df33-1d65-4082-9429-7719a37de051 |  glance  |     image     | completed | 19da365c-ddb4-432c-92f2-60b966d347fe | 44659c49-36cd-4ea9-863e-e39916370be0 |
  | 7d3449c3-a542-48d7-ab99-0649dd066976 |  glance  |     image     | completed | f02d3b07-7008-486d-b298-a08b1b1f3e2e | 93df67bc-fb7a-4bfa-89a7-3dbfa859472e |
  | 0984b0c0-a5a0-459d-8132-548ca8e6574f | keystone |     domain    | completed |   38da677b7dd944f8bce50bba4342bda6   |   6f05f02ce89b4976bb6f06bce3d2a40a   |
  | 75261d19-42a0-4b96-9012-b648d2cc10b9 | keystone |    project    | completed |   609c48d29a1b483cb2d8a75bc84abdf7   |   d1872c224487448cbea6408cce156bef   |
  | 7dc686ad-8ba3-476b-b0e5-b3568513a2d6 |  glance  |     image     | completed | 161081e2-6617-471e-b341-c2e7b42201b8 | fa30ed55-22e2-4bd0-8550-1e8f3baaad37 |
  | 08a69ab8-eab6-43b3-9756-6a530eeec09f |  glance  |     image     | completed | 5199e62b-4dac-4a9d-b8b2-7b616e270ea6 | d0accda5-3120-43e2-8bc8-80ef8e701ee4 |
  | 3204f867-0124-4bf1-88ba-bad7c3ec37be | keystone |      user     | completed |   7c58db938ee744c5b14a966a2fb8ed1e   |   2aa41d61e1c94d27b6cdab56c7003b9f   |
  | 66d03194-53de-462e-9812-b12a8962690d | keystone |    project    | completed |   cfc158bad223468c82c6570486113a4d   |   080674ff96894e04a077274bede11b26   |
  | 4fb1e97c-0850-46ff-a4eb-f21bcad03a7a |  glance  |     image     | completed | f4631001-e724-405d-a50c-d1e8cfbf618c | e4453093-2de5-44b1-b3ae-01a050bd2491 |
  | 9465d306-344f-4430-9ed0-3f932a824727 | neutron  |      port     | completed | a21256ea-dc86-4560-ab75-44a53f950ea7 | 1a475258-0a60-443d-acdd-daa303746632 |
  | 558b900b-e8ae-482f-a044-c440058bbf25 |   nova   |    instance   | completed | e54d012c-ff5d-4e26-9a79-6829aa191450 | 4f9e1849-a2d4-4aed-a43c-2158278c6d77 |
  | abd5745d-79ca-4851-bbf3-5fbd76c875a3 |  glance  |     image     | completed | 3f46206f-ee62-4c5f-ab7a-748904b72e59 | 2472ef15-5dc8-43e0-8017-b90d976184c9 |
  | 0c32a114-d944-4675-a6a3-b9410338ff21 |   nova   |     flavor    | completed | f128eb24-47ec-427a-a2a6-ccfbafce105f | 10f6b1f2-72e0-4d76-a245-0ae38d37d078 |
  | 656db9d7-6bbe-4c73-b31e-51fbf785ce18 | neutron  |      port     | completed | 58d59325-ccd8-42c4-9b6f-779335eb20a9 | c2045210-6599-4967-9dce-bc6c9cb84f0a |
  | 507a1504-fb7a-4810-a55b-31fe2875cec2 |   nova   |    instance   | completed | 7d65f412-f074-49e5-bd50-0cfcbad1e982 | 06b84ecf-9635-470a-bf16-91faf3d62102 |
  | 44816873-d770-421e-b50b-8ae9b26a4949 | neutron  |     subnet    | completed | a428d163-5a5b-4c0a-bee2-b0b025464957 | e3803961-6816-47e2-89ac-977affa68eec |
  | cc6b998c-550c-4060-a91b-161dd6ed3d8a | neutron  |    network    | completed | 51af7bff-b5f6-4d1b-95e6-1f540ef91995 | 0a1dd38f-ed68-4b00-b4ef-6466c3694df1 |
  +--------------------------------------+----------+---------------+-----------+--------------------------------------+--------------------------------------+

Each migration is identified through an UUID. We can obtain more details about
a given migration like so:

.. code-block:: none

  sunbeam-migrate show 0209b968-10ae-4770-ac6e-6c454fb4323f

  +----------------------------------------------------------+
  |                        Migration                         |
  +-------------------+--------------------------------------+
  |       Field       |                Value                 |
  +-------------------+--------------------------------------+
  |        Uuid       | 0209b968-10ae-4770-ac6e-6c454fb4323f |
  |     Created at    |      2025-12-16 14:15:08.361107      |
  |     Updated at    |      2025-12-16 14:15:17.140378      |
  |      Service      |                glance                |
  |   Resource type   |                image                 |
  |    Source cloud   |             source-admin             |
  | Destination cloud |          destination-admin           |
  |     Source id     | 5f7f24cc-b700-4195-80af-50e61adff91d |
  |   Destination id  | e1a526cf-1ac5-4532-a5f8-1069ea585c22 |
  |       Status      |              completed               |
  |   Error message   |                 None                 |
  |      Archived     |                False                 |
  |   Source removed  |                False                 |
  |      External     |                False                 |
  +-------------------+--------------------------------------+
