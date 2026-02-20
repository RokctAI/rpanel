"""
System User Manager for rpanel

Manages Linux system users for website isolation with reference counting.
Ensures users are only deleted when no websites reference them.
"""

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
            result = subprocess.run(
                ['id', username],
                capture_output=True,
                text=True
            )
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
                frappe.msgprint(f"User {username} already exists")
                return

            # Create user with no shell access
            subprocess.run([
                'sudo', 'useradd',
                '-M',  # No home directory
                '-s', '/bin/false',  # No shell access
                '-g', 'www-data',  # Primary group: www-data
                username
            ], check=True)

            # Create web directory for user
            web_dir = f"/var/www/{username}"
            if not os.path.exists(web_dir):
                subprocess.run(['sudo', 'mkdir', '-p', web_dir], check=True)
                subprocess.run(['sudo', 'chown', f'{username}:www-data', web_dir], check=True)
                subprocess.run(['sudo', 'chmod', '750', web_dir], check=True)

            frappe.msgprint(f"Created system user: {username}")

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
            subprocess.run([
                'sudo', 'userdel',
                username
            ], check=True)

            frappe.msgprint(f"Deleted system user: {username}")

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
        if frappe.db.exists("System User Reference", {"user_name": username, "site_name": site_name}):
            return

        # Create reference record
        frappe.get_doc({
            "doctype": "System User Reference",
            "user_name": username,
            "site_name": site_name
        }).insert(ignore_permissions=True)
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
            pluck="name"
        )

        for ref_name in refs:
            frappe.delete_doc("System User Reference", ref_name, ignore_permissions=True)

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
                ['id', username],
                capture_output=True,
                text=True,
                check=True
            )
            return {'exists': True, 'info': result.stdout}
        except subprocess.CalledProcessError:
            return {'exists': False}


@frappe.whitelist()
def list_system_users():
    """List all system users managed by rpanel"""
    users = frappe.db.sql("""
        SELECT DISTINCT user_name, COUNT(site_name) as site_count
        FROM `tabSystem User Reference`
        GROUP BY user_name
        ORDER BY user_name
    """, as_dict=True)

    return {'success': True, 'users': users}


@frappe.whitelist()
def get_user_sites(username):
    """Get all sites using a specific system user"""
    sites = frappe.get_all(
        "System User Reference",
        filters={"user_name": username},
        fields=["site_name"],
        pluck="site_name"
    )

    return {'success': True, 'sites': sites}
