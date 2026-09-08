# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from rpanel.hosting.vps.ovh import OVHVPSProvider
from rpanel.hosting.vps.hetzner import HetznerVPSProvider
from rpanel.hosting.vps.hostinger import HostingerVPSProvider
from rpanel.hosting.vps.provider import VPSProvider


class VPSPoolManager(VPSProvider):
    """
    Composite VPS provider acting as a failover pool.
    Cascades server creation requests down the list of active providers
    (OVH -> Hetzner -> Hostinger) when stock/API constraints occur.
    """

    def __init__(self, provider_priority=None):
        priority = provider_priority or frappe.conf.get("vps_pool_priority")
        if not priority:
            priority = ["ovh", "hetzner", "hostinger"]
        elif isinstance(priority, str):
            priority = [p.strip().lower() for p in priority.split(",")]

        self.pool = []
        for p in priority:
            try:
                prov = get_single_provider(p)
                if prov:
                    self.pool.append((p, prov))
            except Exception as e:
                frappe.log_error(
                    f"Failed to load provider '{p}' into pool: {e}",
                    "VPS Pool Init Error",
                )

    def create_vps(self, plan_code: str, site_name: str, **kwargs) -> dict:
        """
        Attempts to provision a VPS in sequence across the pool providers.
        """
        errors = []
        for name, provider in self.pool:
            try:
                frappe.log(
                    f"VPS Pool Manager: Attempting creation with provider '{name}' for {site_name}"
                )
                res = provider.create_vps(plan_code, site_name, **kwargs)
                if res and res.get("status") == "success":
                    res["provider"] = name
                    frappe.log(
                        f"VPS Pool Manager: SUCCESS with provider '{name}' for {site_name}"
                    )
                    return res
                else:
                    err_str = res.get("error") if res else "Unknown provider failure"
                    errors.append(f"{name}: {err_str}")
                    frappe.log(f"VPS Pool Manager: Provider '{name}' failed: {err_str}")
            except Exception as e:
                errors.append(f"{name}: Exception: {str(e)}")
                frappe.log_error(
                    f"VPS Pool Manager: Exception on provider '{name}': {e}",
                    "VPS Pool Cascading Error",
                )

        # If we reach here, all providers in the pool failed
        err_summary = " | ".join(errors)
        frappe.log_error(
            f"VPS Pool exhausted. All creations failed: {err_summary}",
            "VPS Pool Exhaustion",
        )
        return {
            "status": "failed",
            "error": f"VPS pool exhausted. Failed on all providers: {err_summary}",
        }

    def _find_provider_for_id(self, vps_id: str):
        """
        Heuristically identifies which provider controls the given VPS ID.
        """
        vps_id_str = str(vps_id).lower()
        if "ovh" in vps_id_str or ".net" in vps_id_str:
            return "ovh", get_single_provider("ovh")

        # For numeric/other IDs, we probe active providers
        for name, provider in self.pool:
            if name == "ovh":
                continue  # Already handled specifically by name
            try:
                status = provider.get_vps_status(vps_id)
                if status and status.get("state") != "unknown":
                    return name, provider
            except Exception:
                continue

        # Fallback to first provider in pool
        if self.pool:
            return self.pool[0][0], self.pool[0][1]
        return "ovh", get_single_provider("ovh")

    def rebuild_vps(
        self, vps_id: str, image_name: str, ssh_keys: list, **kwargs
    ) -> bool:
        name, provider = self._find_provider_for_id(vps_id)
        return provider.rebuild_vps(vps_id, image_name, ssh_keys, **kwargs)

    def get_vps_status(self, vps_id: str) -> dict:
        name, provider = self._find_provider_for_id(vps_id)
        return provider.get_vps_status(vps_id)

    def reboot_vps(self, vps_id: str, hard: bool = False) -> bool:
        name, provider = self._find_provider_for_id(vps_id)
        return provider.reboot_vps(vps_id, hard)

    def terminate_vps(self, vps_id: str, **kwargs) -> bool:
        name, provider = self._find_provider_for_id(vps_id)
        return provider.terminate_vps(vps_id, **kwargs)


def get_single_provider(provider_type: str, **kwargs) -> object:
    provider_type = provider_type.lower().strip()
    if provider_type == "ovh":
        return OVHVPSProvider(**kwargs)
    elif provider_type == "hetzner":
        return HetznerVPSProvider(**kwargs)
    elif provider_type == "hostinger":
        return HostingerVPSProvider(**kwargs)
    else:
        raise ValueError(f"Unsupported VPS provider: '{provider_type}'")


def get_vps_provider(provider_type: str = None, **kwargs) -> object:
    """
    Factory method to dynamically retrieve the correct VPS provider instance.
    If 'pool' or None is specified, returns the composite VPSPoolManager.

    Usage:
            provider = get_vps_provider() # returns failover pool
            status = provider.get_vps_status("vps-xxxx.ovh.net")
    """
    provider_type = provider_type or frappe.conf.get("default_vps_provider") or "pool"
    provider_type = provider_type.lower().strip()

    if provider_type == "pool":
        return VPSPoolManager(**kwargs)
    else:
        return get_single_provider(provider_type, **kwargs)
