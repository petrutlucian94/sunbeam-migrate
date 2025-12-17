Migrating load balancers
========================

Octavia load balancers are migrated along with all their components:
listeners, pools, members, and health monitors.

Use ``--include-dependencies`` to automatically migrate the VIP network and
subnet. The flag should also be used in multi-tenant mode to automatically
migrate Keystone dependencies.

.. code-block:: none

  sunbeam-migrate start \
    --resource-type=load-balancer \
    --include-dependencies \
    f76d0bf1-bbb9-45cb-94d5-a7cbc7647bbd

  2025-12-05 14:44:59,67 INFO Initiating load-balancer migration, resource id: f76d0bf1-bbb9-45cb-94d5-a7cbc7647bbd
  2025-12-05 14:45:01,478 INFO Migrating associated subnet resource: dfa7fa45-efb1-477b-8d91-64e7c02a93e8
  2025-12-05 14:45:01,486 INFO Initiating subnet migration, resource id: dfa7fa45-efb1-477b-8d91-64e7c02a93e8
  2025-12-05 14:45:03,633 INFO Migrating associated network resource: 72505950-631c-4c6a-b52e-e5ee4c227aeb
  2025-12-05 14:45:03,634 INFO Initiating network migration, resource id: 72505950-631c-4c6a-b52e-e5ee4c227aeb
  2025-12-05 14:45:09,123 INFO Successfully migrated resource, destination id: 8caee94f-0c0f-47a8-8641-f7dfba9927e0
  2025-12-05 14:45:16,816 INFO Successfully migrated resource, destination id: e6235058-dea0-4bd4-9108-4f1098d680e5
  2025-12-05 14:45:16,819 INFO Associated resource network 72505950-631c-4c6a-b52e-e5ee4c227aeb already completed (migration dfc323a6-17ed-46f9-8227-c513f3c1192a), skipping duplicate migration
  2025-12-05 14:45:20,178 INFO Gathering load balancer components from source: f76d0bf1-bbb9-45cb-94d5-a7cbc7647bbd
  2025-12-05 14:45:29,515 INFO Created load balancer 97e19b30-f194-4341-ad3a-aa8cec9b7002 on destination (source: f76d0bf1-bbb9-45cb-94d5-a7cbc7647bbd)
  2025-12-05 14:45:36,568 INFO Created listener e28c6562-cb9c-4c96-9743-d151ddb482df on destination (source: 9b900e12-af9f-4765-9d89-dda878adf237)
  2025-12-05 14:45:42,436 INFO Created pool aefc5bb6-fda1-4fb2-a9b6-17bb4c27c328 on destination (source: ef2feeae-e2a0-4f2f-a20f-fe5dfd4ddcb2)
  2025-12-05 14:45:48,210 INFO Created health monitor 99df81df-9d1f-4904-8431-fd72706b4d03 on destination (source: c7d07146-bf1b-4fd4-9ccf-00d6e6a2e6e4)
  2025-12-05 14:45:57,151 INFO Created member bbe5c728-4e08-4469-85f9-78dd134a0696 in pool aefc5bb6-fda1-4fb2-a9b6-17bb4c27c328 on destination (source: 3f8bd027-5c88-482e-8864-be355ac6654e)
  2025-12-05 14:46:05,279 INFO Created member 0acee607-7c59-4cf9-9381-468a0f3d119c in pool aefc5bb6-fda1-4fb2-a9b6-17bb4c27c328 on destination (source: 74badb77-f27e-4104-bcba-b2404c661bf5)
  2025-12-05 14:46:10,617 INFO Successfully migrated resource, destination id: 97e19b30-f194-4341-ad3a-aa8cec9b7002

The migration process consists in:

1. **Gather components** from the source load balancer (listeners, pools, members, health monitors)
2. **Create the load balancer** on the destination with the VIP settings
3. **Create listeners** one by one, waiting for the LB to be ACTIVE between operations
4. **Create pools** associated with each listener
5. **Create health monitors** for pools that have them
6. **Create members** in each pool with their subnet mappings
