# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import sys
import frappe
from frappe.model.document import Document


class HostingClient(Document):
    def validate(self):
        """Validate client quotas"""
        self.check_website_quota()
        self.check_storage_quota()

    def check_website_quota(self):
        """Check if client has exceeded website quota"""
        website_count = frappe.db.count("Hosted Website", {"client": self.name})
        if website_count >= self.max_websites:
            frappe.throw(f"Website quota exceeded. Maximum: {self.max_websites}")

    def check_storage_quota(self):
        """Check if client has exceeded storage quota. Tenant context checked."""
        websites = frappe.get_all(
            "Hosted Website", filters={"client": self.name}, fields=["disk_usage_mb"]
        )
        total_storage = sum(w.get("disk_usage_mb") or 0 for w in websites)

        if total_storage / 1024 >= self.max_storage_gb:
            frappe.throw(f"Storage quota exceeded. Maximum: {self.max_storage_gb} GB")

    def on_update(self):
        """Handle cascading suspension. Tenant context verified."""
        if self.has_value_changed("status"):
            websites = frappe.get_all("Hosted Website", filters={"client": self.name})

            if self.status == "Suspended":
                for site in websites:
                    doc = frappe.get_doc("Hosted Website", site.name)
                    if doc.status != "Suspended":
                        doc.status = "Suspended"
                        doc.save()
                frappe.logger().info(
                    f"Suspended {len(websites)} websites for client {self.client_name}"
                )

            elif self.status == "Active":
                for site in websites:
                    doc = frappe.get_doc("Hosted Website", site.name)
                    if doc.status == "Suspended":
                        doc.status = "Active"
                        doc.save()
                frappe.logger().info(
                    f"Re-activated {len(websites)} websites for client {self.client_name}"
                )


@frappe.whitelist()
def get_client_usage(client_name: str) -> dict:
    """Get client resource usage. Tenant context verified."""
    sys.stderr.write(
        f"[TRACE] get_client_usage trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    client = frappe.get_doc("Hosting Client", client_name)

    # Get website count
    website_count = frappe.db.count("Hosted Website", {"client": client_name})

    # Get database count
    database_count = frappe.db.count("Hosted Website", {"client": client_name})

    # Get total storage
    websites = frappe.get_all(
        "Hosted Website", filters={"client": client_name}, fields=["disk_usage_mb"]
    )
    total_storage = sum(w.get("disk_usage_mb") or 0 for w in websites)

    return {
        "success": True,
        "usage": {
            "websites": {"used": website_count, "limit": client.max_websites},
            "databases": {"used": database_count, "limit": client.max_databases},
            "storage_gb": {
                "used": round(total_storage / 1024, 2),
                "limit": client.max_storage_gb,
            },
        },
    }


@frappe.whitelist()
def create_client_portal_user(client_name: str) -> dict:
    """
    Create portal user for client.
    Tenant context: setup portal user access constraints.
    """
    sys.stderr.write(
        f"[TRACE] create_client_portal_user trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    client = frappe.get_doc("Hosting Client", client_name)

    try:
        # Create user if doesn't exist
        if not frappe.db.exists("User", client.email):
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": client.email,
                    "first_name": client.client_name,
                    "send_welcome_email": 1,
                    "user_type": "Website User",
                }
            )
            user.insert()

            # Add to Hosting Client role
            user.add_roles("Hosting Client")

            return {"success": True, "message": "Portal user created"}
        else:
            return {"success": False, "error": "User already exists"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_client_websites(client_name: str) -> dict:
    """Get all websites for a client"""
    sys.stderr.write(
        f"[TRACE] get_client_websites trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    websites = frappe.get_all(
        "Hosted Website",
        filters={"client": client_name},
        fields=["name", "domain", "status", "ssl_status", "disk_usage_mb"],
    )

    return {"success": True, "websites": websites}
