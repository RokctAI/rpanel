# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import ovh
import frappe
from rpanel.hosting.vps.provider import VPSProvider


class OVHVPSProvider(VPSProvider):
    """
    Concrete VPS Provider implementation for OVH Cloud Services.
    Utilizes the official 'ovh' Python SDK.
    """

    def __init__(self, endpoint: str = None, **kwargs):
        # Leverage in-memory keys from frappe configs, environment, or custom init args
        endpoint = endpoint or frappe.conf.get("ovh_endpoint") or "ovh-ca"
        self.client = ovh.Client(
            endpoint=endpoint,
            application_key=kwargs.get("application_key")
            or frappe.conf.get("ovh_application_key"),
            application_secret=kwargs.get("application_secret")
            or frappe.conf.get("ovh_application_secret"),
            consumer_key=kwargs.get("consumer_key")
            or frappe.conf.get("ovh_consumer_key"),
        )

    def create_vps(self, plan_code: str, site_name: str, **kwargs) -> dict:
        """
        Places a new order cart for a VPS comfort/basic plan and checks out automatically.
        """
        try:
            subsidiary = kwargs.get(
                "subsidiary", "ZA"
            )  # Default to South Africa / Global billing

            # 1. Initialize cart
            cart = self.client.post("/order/cart", ovhSubsidiary=subsidiary)
            cart_id = cart["cartId"]

            # 2. Assign cart to active user context
            self.client.post(f"/order/cart/{cart_id}/assign")

            # 3. Add designated VPS plan item
            vps_item = self.client.post(
                f"/order/cart/{cart_id}/vps",
                duration=kwargs.get("duration", "P1M"),  # Monthly billing cycles
                planCode=plan_code,
                pricingMode=kwargs.get(
                    "pricingMode", "default"
                ),  # "default" pricing mode has no commitment
            )

            # 4. Trigger auto-checkout (bills registered default credit card/balance on file)
            order = self.client.post(f"/order/cart/{cart_id}/checkout")

            frappe.log(
                f"SUCCESS: OVH Order placed for VPS {site_name} (Order ID: {order.get('orderId')})"
            )

            return {
                "status": "success",
                "order_id": order.get("orderId"),
                "invoice_id": order.get("invoiceId"),
                "url": order.get("url"),
            }
        except Exception as e:
            frappe.log_error(
                f"OVH VPS Order Failed for {site_name}: {e}", "VPS Orchestrator Error"
            )
            return {"status": "failed", "error": str(e)}

    def rebuild_vps(
        self, vps_id: str, image_name: str, ssh_keys: list, **kwargs
    ) -> bool:
        """
        Re-installs the VPS OS utilizing the chosen template and authorized SSH keys.
        """
        try:
            self.client.post(
                f"/vps/{vps_id}/rebuild", templateName=image_name, sshKey=ssh_keys
            )
            return True
        except Exception as e:
            frappe.log_error(
                f"OVH Rebuild Failed for {vps_id}: {e}", "VPS Orchestrator Error"
            )
            return False

    def get_vps_status(self, vps_id: str) -> dict:
        """
        Retrieves active power states, DNS names, and system details.
        """
        try:
            info = self.client.get(f"/vps/{vps_id}")
            return {
                "vps_id": vps_id,
                "state": info.get("state"),  # e.g., 'running', 'stopped', 'maintenance'
                "ip": info.get("name"),  # Primary IP or hostname mapping
                "memory": info.get("memoryLimit"),  # RAM limit in MB
                "vcpus": info.get("vcores"),  # Number of active CPU cores
                "raw_info": info,
            }
        except Exception as e:
            frappe.log_error(
                f"OVH Status Query Failed for {vps_id}: {e}", "VPS Orchestrator Error"
            )
            return {"vps_id": vps_id, "state": "unknown", "error": str(e)}

    def reboot_vps(self, vps_id: str, hard: bool = False) -> bool:
        """
        Triggers a reboot instruction on the virtual instance.
        """
        try:
            # OVH reboot is asynchronous; returns a tasks object
            self.client.post(f"/vps/{vps_id}/reboot")
            return True
        except Exception as e:
            frappe.log_error(
                f"OVH Reboot Failed for {vps_id}: {e}", "VPS Orchestrator Error"
            )
            return False

    def terminate_vps(self, vps_id: str, **kwargs) -> bool:
        """
        Permanently terminates the VPS service on OVH.
        """
        try:
            # OVH API to cancel/terminate the service
            self.client.post(f"/vps/{vps_id}/terminate")
            return True
        except Exception as e:
            frappe.log_error(
                f"OVH VPS Termination Failed for {vps_id}: {e}",
                "VPS Orchestrator Error",
            )
            return False
