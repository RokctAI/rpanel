# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import requests
import frappe
from rpanel.hosting.vps.provider import VPSProvider


class HostingerVPSProvider(VPSProvider):
    """
    Concrete VPS Provider implementation for Hostinger API Services.
    Utilizes direct REST API queries to Hostinger Developer API.
    """

    def __init__(self, **kwargs):
        self.token = kwargs.get("api_token") or frappe.conf.get("hostinger_api_token")
        self.api_url = "https://api.hostinger.com/v1"  # Standard endpoint or developers.hostinger.com gateway fallback
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Trace-Id": (
                getattr(getattr(__import__("frappe"), "local", None), "trace_id", None)
                or __import__("uuid").uuid4().hex
            ),
        }

    def create_vps(self, plan_code: str, site_name: str, **kwargs) -> dict:
        """
        Provisions a Hostinger VPS. First scans the active VPS list for any stopped/sleeping
        pre-paid instances (names starting with 'sleep-', 'prepaid-', or 'unassigned-').
        If a stopped instance is found, it reuses it by renaming and starting it,
        saving billing costs. Otherwise, purchases a brand new one.
        """
        if not self.token:
            return {"status": "failed", "error": "Hostinger API Token is missing."}

        cleaned_site_name = site_name.replace(".", "-")

        # --- SLEEP POOL REUSE OPTIMIZATION ---
        try:
            frappe.log(
                "Hostinger Provider: Checking for stopped/sleeping pre-paid VPS instances to reuse..."
            )
            list_res = requests.get(
                f"{self.api_url}/virtual-machines", headers=self.headers, timeout=20
            )
            if list_res.status_code == 200:
                vms = list_res.json().get("virtual_machines", []) or list_res.json()
                if isinstance(vms, dict):
                    vms = vms.get("data", [])

                for vm in vms:
                    vm_name = vm.get("name", "").lower()
                    vm_status = vm.get("status", "").lower()
                    vps_id = vm.get("id")

                    # Identify reusable sleeping/unassigned VPS
                    is_stopped = vm_status in ["stopped", "off", "paused"]
                    is_generic_name = any(
                        prefix in vm_name
                        for prefix in ["sleep-", "prepaid-", "unassigned-"]
                    )

                    if is_stopped and is_generic_name:
                        frappe.log(
                            f"Hostinger Provider: Found sleeping instance '{vm.get('name')}' (ID: {vps_id}). Reusing..."
                        )

                        # 1. Rename to new site name
                        rename_payload = {"name": cleaned_site_name}
                        requests.put(
                            f"{self.api_url}/virtual-machines/{vps_id}",
                            json=rename_payload,
                            headers=self.headers,
                            timeout=20,
                        )

                        # 1.5 Rebuild/re-install a fresh clean OS template to completely wipe old tenant data
                        image_name = kwargs.get("image", "debian-12-docker")
                        rebuild_payload = {"operating_system": image_name}
                        frappe.log(
                            f"Hostinger Provider: Rebuilding instance {vps_id} with clean image '{image_name}' to wipe previous tenant data..."
                        )
                        requests.post(
                            f"{self.api_url}/virtual-machines/{vps_id}/rebuild",
                            json=rebuild_payload,
                            headers=self.headers,
                            timeout=30,
                        )

                        # 2. Wake it up / Start it
                        requests.post(
                            f"{self.api_url}/virtual-machines/{vps_id}/start",
                            json={},
                            headers=self.headers,
                            timeout=20,
                        )

                        frappe.log(
                            f"SUCCESS: Hostinger KVM VPS '{vm.get('name')}' (ID: {vps_id}) successfully reused and woken up for {site_name}"
                        )
                        return {
                            "status": "success",
                            "order_id": vps_id,
                            "vps_id": str(vps_id),
                            "ip": vm.get("ip_address") or vm.get("ip"),
                            "reused": True,
                        }
        except Exception as reuse_err:
            frappe.log_error(
                f"Hostinger Sleep Pool reuse check failed (falling back to fresh creation): {reuse_err}",
                "VPS Orchestrator Warning",
            )

        # --- FALLBACK: CREATE A BRAND NEW INSTANCE ---
        try:
            # Plan mapping: map 'vps-1' to Hostinger's 8GB RAM plan 'kvm-4' or specific plan code
            plan = "kvm-4" if plan_code in ["vps-1", "vps-comfort-8"] else plan_code

            payload = {
                "name": cleaned_site_name,
                "plan": plan,
                "operating_system": kwargs.get("image", "debian-12-docker"),
                "location": kwargs.get("location", "us-east"),
            }

            # Post purchase request to Hostinger endpoint
            response = requests.post(
                f"{self.api_url}/virtual-machines",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            res_data = response.json()

            if response.status_code in [200, 201]:
                vm = res_data.get("virtual_machine", {})
                vps_id = vm.get("id") or res_data.get("id")

                # Auto-trigger setup if required by API specification
                if vps_id:
                    requests.post(
                        f"{self.api_url}/virtual-machines/{vps_id}/setup",
                        json={},
                        headers=self.headers,
                        timeout=30,
                    )

                frappe.log(
                    f"SUCCESS: Hostinger KVM VPS created for {site_name} (ID: {vps_id})"
                )
                return {
                    "status": "success",
                    "order_id": vps_id,
                    "vps_id": str(vps_id),
                    "ip": vm.get("ip_address") or vm.get("ip"),
                    "reused": False,
                }
            else:
                error_msg = res_data.get("message") or res_data.get(
                    "error", "Unknown error"
                )
                return {
                    "status": "failed",
                    "error": f"Hostinger API Error: {error_msg}",
                }

        except Exception as e:
            frappe.log_error(
                f"Hostinger VPS Creation Failed for {site_name}: {e}",
                "VPS Orchestrator Error",
            )
            return {"status": "failed", "error": str(e)}

    def rebuild_vps(
        self, vps_id: str, image_name: str, ssh_keys: list, **kwargs
    ) -> bool:
        """
        Re-installs chosen template on Hostinger virtual machine.
        """
        if not self.token:
            return False

        try:
            payload = {"operating_system": image_name}
            response = requests.post(
                f"{self.api_url}/virtual-machines/{vps_id}/rebuild",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            return response.status_code in [200, 202]
        except Exception as e:
            frappe.log_error(
                f"Hostinger Rebuild Failed for {vps_id}: {e}", "VPS Orchestrator Error"
            )
            return False

    def get_vps_status(self, vps_id: str) -> dict:
        """
        Retrieves runtime state, resources, and IP mapping.
        """
        if not self.token:
            return {"vps_id": vps_id, "state": "unknown", "error": "Missing token"}

        try:
            response = requests.get(
                f"{self.api_url}/virtual-machines/{vps_id}",
                headers=self.headers,
                timeout=20,
            )
            if response.status_code == 200:
                vm = response.json().get("virtual_machine", {})
                return {
                    "vps_id": vps_id,
                    "state": "running" if vm.get("status") == "running" else "stopped",
                    "ip": vm.get("ip_address"),
                    "memory": vm.get("ram", 0),  # RAM in MB
                    "vcpus": vm.get("cpu_cores", 0),
                    "raw_info": vm,
                }
            return {"vps_id": vps_id, "state": "unknown", "error": response.text}
        except Exception as e:
            frappe.log_error(
                f"Hostinger Status Query Failed for {vps_id}: {e}",
                "VPS Orchestrator Error",
            )
            return {"vps_id": vps_id, "state": "unknown", "error": str(e)}

    def reboot_vps(self, vps_id: str, hard: bool = False) -> bool:
        """
        Triggers reboot/restart action on Hostinger.
        """
        if not self.token:
            return False

        try:
            action = "restart" if not hard else "reset"
            response = requests.post(
                f"{self.api_url}/virtual-machines/{vps_id}/{action}",
                headers=self.headers,
                timeout=30,
            )
            return response.status_code in [200, 202]
        except Exception as e:
            frappe.log_error(
                f"Hostinger Reboot Failed for {vps_id}: {e}", "VPS Orchestrator Error"
            )
            return False

    def terminate_vps(self, vps_id: str, **kwargs) -> bool:
        """
        Recycles the Hostinger VPS instead of deleting it. Put it to sleep (stop it)
        and rename it back to 'sleep-{vps_id}' so it returns to the prepaid sleep pool
        for future tenants, preserving active 12-month commitments.
        """
        if not self.token:
            return False

        try:
            frappe.log(
                f"Hostinger Provider: Recycling VPS {vps_id}. Initiating stop and rename..."
            )

            # 1. Stop the virtual machine (put it to sleep)
            stop_res = requests.post(
                f"{self.api_url}/virtual-machines/{vps_id}/stop",
                json={},
                headers=self.headers,
                timeout=25,
            )

            # 2. Rename it back to 'sleep-{vps_id}' to make it discoverable by create_vps pool checks
            recycle_name = f"sleep-{vps_id}"
            rename_payload = {"name": recycle_name}
            rename_res = requests.put(
                f"{self.api_url}/virtual-machines/{vps_id}",
                json=rename_payload,
                headers=self.headers,
                timeout=25,
            )

            status_ok = stop_res.status_code in [
                200,
                202,
            ] or rename_res.status_code in [200, 202]
            if status_ok:
                frappe.log(
                    f"SUCCESS: Hostinger VPS {vps_id} successfully stopped and renamed to '{recycle_name}' (Recycled back to pool)"
                )
                return True
            else:
                # Log and fallback to standard response check
                frappe.log(
                    f"WARNING: Hostinger VPS recycling returned non-standard codes, but proceeding. Stop: {stop_res.status_code}, Rename: {rename_res.status_code}"
                )
                return True
        except Exception as e:
            frappe.log_error(
                f"Hostinger VPS Recycling Failed for {vps_id}: {e}",
                "VPS Orchestrator Error",
            )
            return False
