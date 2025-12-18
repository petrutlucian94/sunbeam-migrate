Installation
------------

``sunbeam-migrate`` is a tool written entirely in Python, as such we
are going to install it in a Python virtual environment.

.. code-block:: shell

  # Install the venv package.
  sudo apt-get install python3-venv

  # Setup a new virtual env.
  python3 -m venv ~/sunbeam-migrate-venv

  # Activate the venv.
  source ~/sunbeam-migrate-venv/bin/activate

  # Install sunbeam-migrate.
  pip3 install git+https://github.com/petrutlucian94/sunbeam-migrate.git@main

Let's verify the installation by getting the list of available commands:

.. code-block:: none

  sunbeam-migrate -h
  Usage: sunbeam-migrate [OPTIONS] COMMAND [ARGS]...

    Migrate resources between Openstack clouds.

    This tool is primarily designed to assist the migration from Charmed
    Openstack to Canonical Openstack (Sunbeam).

  Options:
    -c, --config TEXT
    --debug            Debug logging.
    -h, --help         Show this message and exit.

  Commands:
    capabilities       Describe migration capabilities.
    cleanup-source     Cleanup the source after successful migrations.
    delete             Remove migrations from the sunbeam-migrate database.
    list               List migrations.
    register-external  Register an external migration.
    restore            Restore soft-deleted migrations.
    show               Show migration information.
    start              Migrate an individual resource.
    start-batch        Migrate multiple resources that match the filters.

Please install the ``nfs-common`` package as well if you intend to migrate
Manila NFS shares.

.. code-block:: bash

  sudo apt-get update
  sudo apt-get install -y nfs-common
