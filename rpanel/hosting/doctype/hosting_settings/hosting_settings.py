# Copyright (c) 2025, ROKCT Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import subprocess
import shlex
import os
import requests

class HostingSettings(Document):
    @frappe.whitelist()
    def renew_platform_ssl(self):
        if not self.platform_cert_command:
            frappe.throw("Please define the Platform Cert Command first.")

        self.run_command(self.platform_cert_command, "Renewing Platform SSL")

    @frappe.whitelist()
    def renew_wildcard_ssl(self):
        if not self.wildcard_cert_command:
            frappe.throw("Please define the Wildcard Cert Command first.")

        self.run_command(self.wildcard_cert_command, "Renewing Wildcard SSL")

    @frappe.whitelist()
    def install_roundcube(self):
        """Installs Roundcube Webmail to /var/www/roundcube"""
        target_dir = "/var/www/roundcube"

        if os.path.exists(os.path.join(target_dir, "config", "config.inc.php")):
             frappe.msgprint("Roundcube appears to be already installed.")
             # We could offer update logic here

        frappe.msgprint("Starting Roundcube Installation...")
        try:
            # 1. Database Setup
            db_name = "roundcubemail"
            db_user = "roundcube"
            db_pass = frappe.generate_hash(length=16)

            # Create DB & User (Idempotent)
            subprocess.run(["sudo", "mysql", "-e", f"CREATE DATABASE IF NOT EXISTS `{db_name}`;"], check=True)
            subprocess.run(["sudo", "mysql", "-e", f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_pass}';"], check=True)
            # Note: If user exists, password won't update. If we want to rotate, we'd need ALTER USER.
            # Assuming fresh install or same pass.

            subprocess.run(["sudo", "mysql", "-e", f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_user}'@'localhost';"], check=True)
            subprocess.run(["sudo", "mysql", "-e", "FLUSH PRIVILEGES;"], check=True)

            # 2. Download & Extract
            # Latest stable URL (Hardcoded for safety/stability)
            download_url = "https://github.com/roundcube/roundcubemail/releases/download/1.6.9/roundcubemail-1.6.9-complete.tar.gz"
            tmp_tar = "/tmp/roundcube.tar.gz"
            tmp_extract = "/tmp/roundcube_extract"

            subprocess.run(["sudo", "wget", download_url, "-O", tmp_tar], check=True)
            subprocess.run(["sudo", "mkdir", "-p", tmp_extract], check=True)
            subprocess.run(["sudo", "tar", "-xzf", tmp_tar, "-C", tmp_extract], check=True)

            # Move to /var/www/roundcube
            # The tar contains a folder like 'roundcubemail-1.6.9'
            extracted_folder = subprocess.check_output(["ls", tmp_extract], text=True).strip()
            src = os.path.join(tmp_extract, extracted_folder)

            if not os.path.exists(target_dir):
                 subprocess.run(["sudo", "mkdir", "-p", target_dir], check=True)

            # Sync files
            subprocess.run(["sudo", "rsync", "-a", f"{src}/", f"{target_dir}/"], check=True)

            # Cleanup
            subprocess.run(["sudo", "rm", "-rf", tmp_extract, tmp_tar], check=True)

            # 3. Import SQL
            sql_path = os.path.join(target_dir, "SQL", "mysql.initial.sql")
            # Check if table exists to avoid re-importing error?
            # mysql.initial.sql usually creates tables. IF NOT EXISTS?
            # Roundcube's SQL uses CREATE TABLE (no if not exists in older versions).
            # Let's try run it; if fails, assume already done.
            try:
                with open(sql_path, 'r') as sql_file:
                    subprocess.run(["sudo", "mysql", db_name], stdin=sql_file, check=True)
            except subprocess.CalledProcessError:
                pass # Assume tables exist

            # 4. Configure config.inc.php
            # We need a random DES key for 'des_key'
            des_key = frappe.generate_hash(length=24)

            config_content = f"""<?php
$config['db_dsnw'] = 'mysql://{db_user}:{db_pass}@localhost/{db_name}';
$config['default_host'] = 'localhost';
$config['smtp_server'] = 'localhost';
$config['smtp_port'] = 25;
$config['smtp_user'] = '%u';
$config['smtp_pass'] = '%p';
$config['support_url'] = '';
$config['product_name'] = 'ROKCT Webmail';
$config['des_key'] = '{des_key}';
$config['plugins'] = array('archive', 'zipdownload', 'password');
$config['skin'] = 'elastic';
?>"""

            tmp_conf = "/tmp/rc_config.inc.php"
            with open(tmp_conf, "w") as f:
                 f.write(config_content)

            dest_conf = os.path.join(target_dir, "config", "config.inc.php")
            subprocess.run(["sudo", "mv", tmp_conf, dest_conf], check=True)

            # 5. Permissions
            subprocess.run(["sudo", "chown", "-R", "www-data:www-data", target_dir], check=True)
            # Logs and Temp need write
            subprocess.run(["sudo", "chmod", "-R", "775", os.path.join(target_dir, "logs")], check=True)
            subprocess.run(["sudo", "chmod", "-R", "775", os.path.join(target_dir, "temp")], check=True)

            frappe.msgprint("Roundcube Installed Successfully! Access it at /webmail on any hosted site.")

        except Exception as e:
            frappe.log_error(f"Roundcube Install Error: {e}")
            frappe.throw(f"Installation Failed: {e}")

    def run_command(self, command, description):
        try:
            # Split command safely
            cmd_parts = shlex.split(command)

            process = subprocess.run(cmd_parts, capture_output=True, text=True, check=True)
            frappe.msgprint(f"{description} Successful.<br><pre>{process.stdout}</pre>")

        except subprocess.CalledProcessError as e:
            frappe.log_error(f"{description} Failed: {e.stderr}")
            frappe.throw(f"{description} Failed.<br>Error Code: {e.returncode}<br><pre>{e.stderr}</pre>")

@frappe.whitelist()
def get_system_status():
    """Check status of system services"""
    services = ['nginx', 'mysql', 'exim4']
    status = {}
    
    for service in services:
        try:
            result = subprocess.run(
                ['sudo', 'systemctl', 'is-active', service],
                capture_output=True,
                text=True
            )
            status[service] = {
                'status': result.stdout.strip() if result.returncode == 0 else 'inactive'
            }
        except Exception as e:
            status[service] = {'status': 'unknown'}
    
    return status

@frappe.whitelist()
def reload_nginx():
    """Reload Nginx configuration"""
    try:
        subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], check=True)
        return {'success': True, 'message': 'Nginx reloaded successfully'}
    except subprocess.CalledProcessError as e:
        frappe.log_error(f"Nginx reload failed: {e}")
        frappe.throw("Failed to reload Nginx")

@frappe.whitelist()
def test_email(email):
    """Send a test email to verify email configuration"""
    try:
        frappe.sendmail(
            recipients=[email],
            subject='ROKCT Hosting - Test Email',
            message='This is a test email from your ROKCT hosting system. If you received this, email is configured correctly!'
        )
        return {'success': True}
    except Exception as e:
        frappe.log_error(f"Test email failed: {e}")
        return {'success': False, 'error': str(e)}

