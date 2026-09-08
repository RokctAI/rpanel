# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import requests
import frappe
from rpanel.hosting.vps.provider import VPSProvider


class HetznerVPSProvider(VPSProvider):
    """
    Concrete VPS Provider implementation for Hetzner Cloud Services.
    Utilizes direct REST API queries to https://api.hetzner.cloud/v1/
    """

    def __init__(self, **kwargs):
        self.token = kwargs.get("api_token") or frappe.conf.get("hetzner_api_token")
        self.api_url = "https://api.hetzner.cloud/v1"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "X-Trace-Id": (
                getattr(getattr(__import__("frappe"), "local", None), "trace_id", None)
                or __import__("uuid").uuid4().hex
            ),
        }

    def create_vps(self, plan_code: str, site_name: str, **kwargs) -> dict:
        """
        Provisions a brand new Hetzner Cloud server instance dynamically.
        """
        if not self.token:
            return {"status": "failed", "error": "Hetzner API Token is missing."}

        try:
            # Plan code mapping: Map generic plan_code or 'vps-1' to a robust 8GB Hetzner Cloud equivalent ('cpx21')
            # Hetzner CPX21: 3 vCPUs, 8GB RAM, 80GB NVMe SSD (~$10-12/mo)
            server_type = (
                "cpx21" if plan_code in ["vps-1", "vps-comfort-8"] else plan_code
            )

            # Use default location fsn1 (Falkenstein, Germany) or ash (Ashburn, USA) if CA/NA preferred
            location = (
                kwargs.get("location") or frappe.conf.get("hetzner_location") or "fsn1"
            )
            image = (
                kwargs.get("image")
                or frappe.conf.get("hetzner_image")
                or "ubuntu-24.04"
            )

            payload = {
                "name": site_name.replace(".", "-"),
                "server_type": server_type,
                "image": image,
                "location": location,
                "start_after_create": True,
            }

            # Add public SSH Keys if supplied
            ssh_keys = kwargs.get("ssh_keys") or frappe.conf.get("hetzner_ssh_keys")
            if ssh_keys:
                payload["ssh_keys"] = (
                    ssh_keys if isinstance(ssh_keys, list) else [ssh_keys]
                )

            response = requests.post(
                f"{self.api_url}/servers",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            res_data = response.json()

            if response.status_code == 201:
                server = res_data.get("server", {})
                root_password = res_data.get("root_password")

                frappe.log(
                    f"SUCCESS: Hetzner Server created for {site_name} (ID: {server.get('id')})"
                )
                return {
                    "status": "success",
                    "order_id": server.get("id"),
                    "vps_id": str(server.get("id")),
                    "ip": server.get("public_net", {}).get("ipv4", {}).get("ip"),
                    "root_password": root_password,
                }
            else:
                error_msg = res_data.get("error", {}).get("message", "Unknown error")
                return {"status": "failed", "error": f"Hetzner API Error: {error_msg}"}

        except Exception as e:
            frappe.log_error(
                f"Hetzner Server Creation Failed for {site_name}: {e}",
                "VPS Orchestrator Error",
            )
            return {"status": "failed", "error": str(e)}

    def rebuild_vps(
        self, vps_id: str, image_name: str, ssh_keys: list, **kwargs
    ) -> bool:
        """
        Rebuilds the Hetzner server utilizing a designated OS image.
        """
        if not self.token:
            return False

        try:
            payload = {"image": image_name}
            response = requests.post(
                f"{self.api_url}/servers/{vps_id}/actions/rebuild",
                json=payload,
                headers=self.headers,
                timeout=30,
            )
            return response.status_code == 201
        except Exception as e:
            frappe.log_error(
                f"Hetzner Rebuild Failed for {vps_id}: {e}", "VPS Orchestrator Error"
            )
            return False

    def get_vps_status(self, vps_id: str) -> dict:
        """
        Retrieves runtime status metrics and metadata.
        """
        if not self.token:
            return {"vps_id": vps_id, "state": "unknown", "error": "Missing token"}

        try:
            response = requests.get(
                f"{self.api_url}/servers/{vps_id}", headers=self.headers, timeout=20
            )
            if response.status_code == 200:
                server = response.json().get("server", {})
                return {
                    "vps_id": vps_id,
                    "state": "running"
                    if server.get("status") == "running"
                    else "stopped",
                    "ip": server.get("public_net", {}).get("ipv4", {}).get("ip"),
                    "memory": server.get("server_type", {}).get("memory", 0)
                    * 1024,  # Convert GB to MB
                    "vcpus": server.get("server_type", {}).get("cores", 0),
                    "raw_info": server,
                }
            return {"vps_id": vps_id, "state": "unknown", "error": response.text}
        except Exception as e:
            frappe.log_error(
                f"Hetzner Status Query Failed for {vps_id}: {e}",
                "VPS Orchestrator Error",
            )
            return {"vps_id": vps_id, "state": "unknown", "error": str(e)}

    def reboot_vps(self, vps_id: str, hard: bool = False) -> bool:
        """
        Triggers reboot action.
        """
        if not self.token:
            return False

        try:
            action = "reboot" if not hard else "reset"
            response = requests.post(
                f"{self.api_url}/servers/{vps_id}/actions/{action}",
                headers=self.headers,
                timeout=30,
            )
            return response.status_code == 201
        except Exception as e:
            frappe.log_error(
                f"Hetzner Reboot Failed for {vps_id}: {e}", "VPS Orchestrator Error"
            )
            return False

    def terminate_vps(self, vps_id: str, **kwargs) -> bool:
        """
        Permanently deletes the server instance to stop billing.
        """
        if not self.token:
            return False

        try:
            response = requests.delete(
                f"{self.api_url}/servers/{vps_id}", headers=self.headers, timeout=30
            )
            return response.status_code == 200 or response.status_code == 202
        except Exception as e:
            frappe.log_error(
                f"Hetzner Server Deletion Failed for {vps_id}: {e}",
                "VPS Orchestrator Error",
            )
            return False
