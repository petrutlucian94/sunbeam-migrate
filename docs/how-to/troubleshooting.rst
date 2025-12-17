Troubleshooting
===============

Logs
----

Increasing the log level to "debug" can help determining the cause of
``sunbeam-migrate`` failures.

This will also bump the log level of the Openstack SDK, which will log
every HTTP request issued to Openstack services:

.. code-block:: none

  2025-12-17 13:16:52,976 DEBUG REQ: curl -g -i -X GET "http://192.168.121.204:80/openstack-glance/v2/images?owner=609c48d29a1b483cb2d8a75bc84abdf7" -H "Accept: application/json" -H "User-Agent: openstacksdk/4.8.0 keystoneauth1/5.12.0 python-requests/2.32.5 CPython/3.12.3" -H "X-Auth-Token: {SHA256}14876bedfda23e6e13c9c1a42fd1f8eb7c1c450b33ff3303ae14e49dfd1e9c34"
  2025-12-17 13:16:53,800 DEBUG http://192.168.121.204:80 "GET /openstack-glance/v2/images?owner=609c48d29a1b483cb2d8a75bc84abdf7 HTTP/1.1" 200 108
  2025-12-17 13:16:53,800 DEBUG RESP: [200] Content-Length: 108 Content-Type: application/json Date: Wed, 17 Dec 2025 13:16:53 GMT Server: Apache/2.4.58 (Ubuntu) X-Openstack-Request-Id: req-7def5795-3522-458d-80b1-71fc9c4e2a92
  2025-12-17 13:16:53,800 DEBUG RESP BODY: {"images": [], "first": "/v2/images?owner=609c48d29a1b483cb2d8a75bc84abdf7", "schema": "/v2/schemas/images"}
  2025-12-17 13:16:53,801 DEBUG GET call to image for http://192.168.121.204:80/openstack-glance/v2/images?owner=609c48d29a1b483cb2d8a75bc84abdf7 used request id req-7def5795-3522-458d-80b1-71fc9c4e2a92

Use the ``log_level`` config option or the ``--debug`` command-line parameter.

Permission issues
-----------------

Cross-project migrations (multi-tenant mode) require admin privileges. Make sure
that the provided credentials have the necessary permissions.

Not all Openstack services allow specifying a different owner when creating
resources. As such, ``sunbeam-migrate`` needs to use project scoped sessions,
assigning itself as a member of the migrated tenant.

We're using the "member" role name but if the Openstack deployment uses
non-standard role names, please specify it in the ``sunbeam-migrate``
configuration.
