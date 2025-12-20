Vault Secret Migration
======================

Overview
--------

This guide explains how to migrate secrets between two Vault deployments (Charmed Openstack and Sunbeam) using the Vault CLI and a helper script.

The migration process involves:

1. Configuring access to the source Vault (from Charmed Openstack)
2. Configuring access to the destination Vault (vault-k8s from Sunbeam)
3. Exporting secrets from the source Vault
4. Importing secrets into the destination Vault

.. note::

   For Barbican secrets, see the :ref:`migration handler<barbican_secret_ref>` page.

Prerequisites
-------------

Ensure you have the following tools installed:

* ``vault`` CLI (Vault client)
* ``jq`` (JSON processor)
* ``yq`` (YAML processor)

Source Vault Configuration (Machine Charm)
-------------------------------------------

The source Vault is deployed as a Juju machine charm. Follow these steps to configure access:

Step 1: Set the Vault Address
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get the public address of the Vault leader unit and set the ``VAULT_ADDR`` environment variable:

.. code-block:: bash

   export VAULT_ADDR=https://$(juju status vault/leader --format=yaml | awk '/public-address/ { print $2 }'):8200
   echo $VAULT_ADDR

Step 2: Retrieve the CA Certificate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Vault charm uses a self-signed certificate. Retrieve it from Juju secrets:

.. code-block:: bash

   # Find the certificate secret ID
   cert_juju_secret_id=$(juju secrets --format=yaml | yq 'to_entries | .[] | select(.value.label == "self-signed-vault-ca-certificate") | .key')
   echo $cert_juju_secret_id

   # Extract the certificate to a file
   juju show-secret ${cert_juju_secret_id} --reveal --format=yaml | yq '.[].content.certificate' > vault.pem

   # Set the CA certificate path
   export VAULT_CACERT=$PWD/vault.pem
   echo $VAULT_CACERT

.. note::
   You can use either ``VAULT_CACERT`` or ``VAULT_CAPATH``. ``VAULT_CACERT`` points to a single certificate file, while ``VAULT_CAPATH`` points to a directory containing certificates.

Step 3: Enable KV v2 Secrets Engine (If Not Already Done)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable the KV v2 secrets engine if it's not already enabled:

.. code-block:: bash

   vault secrets enable -version=2 kv

Verify you can read/write secrets:

.. code-block:: bash

   # Write a test secret
   vault kv put kv/test password=test123

   # Read it back
   vault kv get kv/test

Destination Vault Configuration (Vault-k8s from Sunbeam)
--------------------------------------------------------

The destination Vault is deployed as vault-k8s inside Sunbeam. The configuration process is similar but adapted for the Kubernetes environment.

Step 1: Set the Vault Address
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get the Vault service address from the Sunbeam cluster:

.. code-block:: bash

   # Get the vault-k8s unit address
   export VAULT_ADDR="https://$(juju status --format=yaml | yq '.applications."vault-k8s".address'):8200"
   echo $VAULT_ADDR

Step 2: Retrieve the CA Certificate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to the source, retrieve the CA certificate for vault-k8s:

.. code-block:: bash

   # Find the certificate secret ID
   cert_juju_secret_id=$(juju secrets --format=yaml | yq 'to_entries | .[] | select(.value.label == "self-signed-vault-ca-certificate") | .key')
   echo $cert_juju_secret_id

   # Extract the certificate
   juju show-secret ${cert_juju_secret_id} --reveal --format=yaml | yq '.[].content.certificate' > vault-k8s.pem

   # Set the CA certificate path
   export VAULT_CACERT=$PWD/vault-k8s.pem

Step 3: Enable KV v2 Secrets Engine (If Not Already Done)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable the KV v2 secrets engine if it's not already enabled:

.. code-block:: bash

   vault secrets enable -version=2 kv

Verify you can read/write secrets:

.. code-block:: bash

   # Write a test secret
   vault kv put kv/test password=test123

   # Read it back
   vault kv get kv/test

Migration Process
-----------------

Once both Vault instances are configured, you can migrate secrets using the migration script below.

The migration script handles both export from the source Vault and import to the destination Vault in a single operation. It manages the environment variables internally, switching between source and destination as needed.

Using the Migration Script
~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
The migration script is provided in the `sunbeam-migrate` repository under `misc/scripts/vault_migrate.sh <https://github.com/petrutlucian94/sunbeam-migrate/blob/main/misc/scripts/vault_migrate.sh>`_. Save the script to your local machine.

.. code-block:: bash

   chmod +x vault_migrate.sh

Run the migration:

.. code-block:: bash

   # Basic usage - migrate all secrets from a mount
   ./vault_migrate.sh \
     --source-addr "https://10.44.77.172:8200" \
     --source-cacert "/path/to/source-vault.pem" \
     --source-token "hvs.source_token" \
     --dest-addr "https://10.5.0.10:8200" \
     --dest-cacert "/path/to/dest-vault.pem" \
     --dest-token "hvs.dest_token" \
     --mount "kv"

   # Migrate from a specific path within a mount
   ./vault_migrate.sh \
     --source-addr "https://10.44.77.172:8200" \
     --source-cacert "/path/to/source-vault.pem" \
     --source-token "hvs.source_token" \
     --dest-addr "https://10.5.0.10:8200" \
     --dest-cacert "/path/to/dest-vault.pem" \
     --dest-token "hvs.dest_token" \
     --mount "kv" \
     --start-path "mypasswords/"

   # Dry run to verify without making changes
   ./vault_migrate.sh \
     --source-addr "https://10.44.77.172:8200" \
     --source-cacert "/path/to/source-vault.pem" \
     --source-token "hvs.source_token" \
     --dest-addr "https://10.5.0.10:8200" \
     --dest-cacert "/path/to/dest-vault.pem" \
     --dest-token "hvs.dest_token" \
     --mount "kv" \
     --dry-run

Script Parameters
~~~~~~~~~~~~~~~~~

**Required:**

* ``--source-addr``: Source Vault address (e.g., `https://10.44.77.172:8200`)
* ``--source-cacert``: Path to source Vault CA certificate
* ``--source-token``: Source Vault authentication token
* ``--dest-addr``: Destination Vault address
* ``--dest-cacert``: Path to destination Vault CA certificate
* ``--dest-token``: Destination Vault authentication token
* ``--mount``: KV mount path to migrate (e.g., "kv")

**Optional:**

* ``--start-path``: Sub-path within the mount (e.g., "mypasswords/")
* ``--dry-run``: Simulate the migration without making changes
* ``--kv-version``: KV secrets engine version (default: 2)

Best Practices
--------------

* **Test with a dry run**: Always use ``--dry-run`` flag first to verify the migration without making changes.
* **Backup existing secrets**: Before migrating, consider backing up any existing secrets in the destination Vault.
* **Verify connectivity**: Test connection to both source and destination Vaults before running the migration:

  .. code-block:: bash

     # Test source
     export VAULT_ADDR=<source-addr>
     export VAULT_CACERT=<source-cacert>
     export VAULT_TOKEN=<source-token>
     vault status

     # Test destination
     export VAULT_ADDR=<dest-addr>
     export VAULT_CACERT=<dest-cacert>
     export VAULT_TOKEN=<dest-token>
     vault status

* **Check permissions**: Ensure your Vault tokens have sufficient permissions:
  
  * Source token: read permissions on the mount path
  * Destination token: write permissions and ability to enable secrets engines if needed

* **Secure token handling**: Be cautious with tokens on the command line as they may be visible in process listings. Consider:
  
  * Using environment variables for tokens
  * Creating short-lived tokens for migration operations

* **Test incrementally**: For large migrations, test with a small subset using ``--start-path`` before migrating everything.
* **Verify the migration**: After importing, manually verify secrets to ensure they were migrated correctly:

  .. code-block:: bash

     # Set destination Vault environment
     export VAULT_ADDR=<dest-addr>
     export VAULT_CACERT=<dest-cacert>
     export VAULT_TOKEN=<dest-token>

     # Verify a migrated secret
     vault kv get kv/mypasswords

* **Monitor the output**: The script provides detailed output showing each secret being exported and imported. Review it for warnings or errors.

Troubleshooting
---------------

Script Fails to Connect to Source Vault
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see "ERROR: Cannot connect to source Vault":

* Verify ``--source-addr`` is correct and the Vault service is accessible:

  .. code-block:: bash

     curl -k <source-addr>/v1/sys/health

* Ensure ``--source-cacert`` points to the correct certificate file
* Check that the certificate file is readable
* Test the connection manually:

  .. code-block:: bash

     export VAULT_ADDR=<source-addr>
     export VAULT_CACERT=<source-cacert>
     vault status

Script Fails to Connect to Destination Vault
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you see "ERROR: Cannot connect to destination Vault":

* Follow the same steps as for source Vault, but with destination parameters
* Ensure the destination Vault is unsealed and accessible
