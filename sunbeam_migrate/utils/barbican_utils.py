# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0


def parse_barbican_url(ref_url) -> str:
    """Extract the resource id from a Barbican URL reference."""
    return (ref_url or "").split("/")[-1]
