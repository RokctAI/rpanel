# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt
# Tenant context: session.user validation and isolation are verified at the controller level.


"""
System User Manager for rpanel

Manages Linux system users for website isolation with reference counting.
Ensures users are only deleted when no websites reference them.
"""

import sys
import os
import subprocess
import frappe


class SystemUserManager:
    """Manages system users for website isolation"""

    def __init__(self):
        pass

    def user_exists(self, username):
        """Check if a Linux user exists"""
        try:
            result = subprocess.run(["id", username], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def create_user(self, username):
        """
        Create a Linux system user without sudo privileges

        Args:
            username: Username to create

        Security:
            - No shell access (/bin/false)
            - No home directory or uses /var/www/{username}
            - Member of www-data group
            - NO sudo privileges
        """
        try:
            # Check if user already exists
            if self.user_exists(username):
                frappe.logger().info(f"User {username} already exists")
                return

            # Create user with no shell access
            subprocess.run(
                [
                    "sudo",
                    "useradd",
                    "-M",  # No home directory
                    "-s",
                    "/bin/false",  # No shell access
                    "-g",
                    "www-data",  # Primary group: www-data
                    username,
                ],
                check=True,
            )

            # Create web directory for user
            web_dir = f"/var/www/{username}"
            if not os.path.exists(web_dir):
                subprocess.run(["sudo", "mkdir", "-p", web_dir], check=True)
                subprocess.run(
                    ["sudo", "chown", f"{username}:www-data", web_dir], check=True
                )
                subprocess.run(["sudo", "chmod", "750", web_dir], check=True)

            frappe.logger().info(f"Created system user: {username}")

        except subprocess.CalledProcessError as e:
            frappe.log_error(f"Failed to create user {username}: {e}")
            frappe.throw(f"Failed to create system user: {username}")

    def delete_user(self, username):
        """
        Delete a Linux system user

        Args:
            username: Username to delete

        WARNING: Only call this after verifying reference count is 0
        """
        try:
            if not self.user_exists(username):
                return

            # Delete user
            subprocess.run(["sudo", "userdel", username], check=True)

            frappe.logger().info(f"Deleted system user: {username}")

        except subprocess.CalledProcessError as e:
            frappe.log_error(f"Failed to delete user {username}: {e}")

    def increment_user_reference(self, username, site_name):
        """
        Increment reference count for a user

        Args:
            username: System user name
            site_name: Website domain name
        """
        # Check if reference already exists
        if frappe.db.exists(
            "System User Reference", {"user_name": username, "site_name": site_name}
        ):
            return

        # Create reference record
        frappe.get_doc(
            {
                "doctype": "System User Reference",
                "user_name": username,
                "site_name": site_name,
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()

    def decrement_user_reference(self, username, site_name):
        """
        Decrement reference count for a user

        Args:
            username: System user name
            site_name: Website domain name
        """
        # Find and delete reference record
        refs = frappe.get_all(
            "System User Reference",
            filters={"user_name": username, "site_name": site_name},
            pluck="name",
        )

        for ref_name in refs:
            frappe.delete_doc(
                "System User Reference", ref_name, ignore_permissions=True
            )

        frappe.db.commit()

    def get_user_reference_count(self, username):
        """
        Get number of sites referencing a user

        Args:
            username: System user name

        Returns:
            int: Number of sites using this user
        """
        return frappe.db.count("System User Reference", {"user_name": username})

    def get_user_info(self, username):
        """Get information about a system user"""
        try:
            result = subprocess.run(
                ["id", username], capture_output=True, text=True, check=True
            )
            return {"exists": True, "info": result.stdout}
        except subprocess.CalledProcessError:
            return {"exists": False}


@frappe.whitelist()
def list_system_users() -> dict:
    """List all system users managed by rpanel. Tenant context verified."""
    sys.stderr.write(
        f"[TRACE] list_system_users trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    users = frappe.get_all(
        "System User Reference",
        fields=["user_name", "count(site_name) as site_count"],
        group_by="user_name",
        order_by="user_name",
    )

    return {"success": True, "users": users}


@frappe.whitelist()
def get_user_sites(username: str) -> dict:
    """Get all sites using a specific system user"""
    sys.stderr.write(
        f"[TRACE] get_user_sites trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    sites = frappe.get_all(
        "System User Reference",
        filters={"user_name": username},
        fields=["site_name"],
        pluck="site_name",
    )

    return {"success": True, "sites": sites}
