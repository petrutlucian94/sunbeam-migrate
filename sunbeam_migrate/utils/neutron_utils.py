# SPDX-FileCopyrightText: 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

from sunbeam_migrate import exception


def get_router_interface_subnets(session, router_id: str) -> list[str]:
    """Get the list of internal subnets connected to a router."""
    router = session.network.get_router(router_id)
    if not router:
        raise exception.NotFound(f"Router not found: {router_id}")

    member_subnet_ids = set()

    internal_owner_prefixes = (
        "network:router_interface",
        "network:router_interface_distributed",
        "network:ha_router_replicated_interface",
    )

    # Fetch all ports whose device_id == router.id
    for port in session.network.ports(device_id=router.id):
        owner = getattr(port, "device_owner", "") or ""
        if not any(owner.startswith(prefix) for prefix in internal_owner_prefixes):
            continue

        for ip in getattr(port, "fixed_ips", []) or []:
            subnet_id = ip.get("subnet_id")
            if subnet_id:
                member_subnet_ids.add(subnet_id)

    return list(member_subnet_ids)
