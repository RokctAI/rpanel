# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


"""
PHP-FPM Pool Manager for rpanel

Creates and manages dedicated PHP-FPM pools for website isolation.
Each site can have its own pool running as a specific system user.
"""

import subprocess
import frappe
from pathlib import Path
from rpanel.hosting.service_intelligence import ServiceIntelligence


class PHPFPMManager:
    """Manages PHP-FPM pools for website isolation"""

    def __init__(self, php_version=None):
        self.php_version = php_version or ServiceIntelligence.get_default_php_version()
        self.pool_dir = Path(ServiceIntelligence.get_php_fpm_pool_dir(self.php_version))

    def create_pool(self, domain, system_user, max_children=5):
        """
        Create dedicated PHP-FPM pool for a site
        """
        socket_path = ServiceIntelligence.get_php_fpm_socket(
            self.php_version, system_user
        )
        pool_file = self.pool_dir / f"{domain}.conf"

        # Check if pool already exists
        if pool_file.exists():
            frappe.logger().info(f"PHP-FPM pool already exists for {domain}")
            return socket_path

        pool_config = f"""[{domain}]
; Pool runs as site-specific user for isolation
user = {system_user}
group = www-data

; Unique socket per site
listen = {socket_path}
listen.owner = www-data
listen.group = www-data
listen.mode = 0660

; Process management
pm = dynamic
pm.max_children = {max_children}
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3

; Security: Disable dangerous functions
php_admin_value[disable_functions] = exec,passthru,shell_exec,system,proc_open,popen,curl_exec,curl_multi_exec,parse_ini_file,show_source,pcntl_exec

; Security: Restrict filesystem access
php_admin_value[open_basedir] = /var/www/{system_user}:/tmp:/usr/share/php

; Logging
php_admin_value[error_log] = /var/log/php{self.php_version}-fpm-{domain}.log
php_admin_flag[log_errors] = on

; Performance
php_admin_value[memory_limit] = 256M
php_admin_value[max_execution_time] = 300
php_admin_value[upload_max_filesize] = 64M
php_admin_value[post_max_size] = 64M
"""

        try:
            # Write pool config
            subprocess.run(
                ["sudo", "tee", str(pool_file)],
                input=pool_config,
                text=True,
                check=True,
                stdout=subprocess.DEVNULL,
            )

            subprocess.run(["sudo", "chmod", "644", str(pool_file)], check=True)

            # Test PHP-FPM config
            result = subprocess.run(
                ["sudo", f"php-fpm{self.php_version}", "-t"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # Config has errors, remove it
                subprocess.run(["sudo", "rm", str(pool_file)], check=True)
                frappe.throw(f"PHP-FPM config error: {result.stderr}")

            # Reload PHP-FPM
            subprocess.run(
                ["sudo", "systemctl", "reload", f"php{self.php_version}-fpm"],
                check=True,
            )

            frappe.logger().info(
                f"Created PHP-FPM pool for {domain} running as {system_user}"
            )
            return socket_path

        except subprocess.CalledProcessError as e:
            frappe.log_error(f"Failed to create PHP-FPM pool: {e}")
            frappe.throw("Failed to create PHP-FPM pool. Check logs.")

    def delete_pool(self, domain):
        """
        Delete PHP-FPM pool for a site

        Args:
            domain: Website domain
        """
        pool_file = self.pool_dir / f"{domain}.conf"

        if not pool_file.exists():
            return

        try:
            subprocess.run(["sudo", "rm", str(pool_file)], check=True)
            subprocess.run(
                ["sudo", "systemctl", "reload", f"php{self.php_version}-fpm"],
                check=True,
            )
            frappe.logger().info(f"Deleted PHP-FPM pool for {domain}")

        except subprocess.CalledProcessError as e:
            frappe.log_error(f"Failed to delete PHP-FPM pool: {e}")

    def pool_exists(self, domain):
        """Check if pool exists for domain"""
        pool_file = self.pool_dir / f"{domain}.conf"
        return pool_file.exists()

    def get_socket_path(self, system_user):
        """Get socket path for a system user"""
        return ServiceIntelligence.get_php_fpm_socket(self.php_version, system_user)


def create_php_pool(domain, system_user, php_version=None):
    """Convenience function to create PHP-FPM pool"""
    manager = PHPFPMManager(php_version)
    return manager.create_pool(domain, system_user)


def delete_php_pool(domain, php_version=None):
    """Convenience function to delete PHP-FPM pool"""
    manager = PHPFPMManager(php_version)
    manager.delete_pool(domain)


@frappe.whitelist()
def test_php_pool(domain):
    """Test if PHP-FPM pool is working"""
    try:
        ver = ServiceIntelligence.get_default_php_version()
        pool_dir = Path(ServiceIntelligence.get_php_fpm_pool_dir(ver))
        pool_file = pool_dir / f"{domain}.conf"

        if not pool_file.exists():
            return {"success": False, "error": "Pool does not exist"}

        # Test PHP-FPM config
        result = subprocess.run(
            ["sudo", f"php-fpm{ver}", "-t"], capture_output=True, text=True
        )

        if result.returncode == 0:
            return {"success": True, "message": "PHP-FPM pool is working"}
        else:
            return {"success": False, "error": result.stderr}

    except Exception as e:
        return {"success": False, "error": str(e)}
