# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate import config


class SunbeamMigrateTestConfig(config.SunbeamMigrateConfig):
    # We're using the "project_cleanup" method of the Openstack SDK
    # to wipe any remaining resources owned by the temporary tenants.
    # It can take about ~30 seconds since it queries all supported services.
    # Use the following setting to disable this step.
    skip_project_purge: bool = False
