# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import subprocess

class FirewallRule(Document):
    def on_insert(self):
        """Apply firewall rule on creation"""
        if self.enabled:
            self.apply_rule()
    
    def on_update(self):
        """Update firewall rule"""
        if self.enabled:
            self.apply_rule()
        else:
            self.remove_rule()
    
    def on_trash(self):
        """Remove firewall rule on deletion"""
        self.remove_rule()
    
    def apply_rule(self):
        """Apply UFW firewall rule"""
        try:
            # Build UFW command
            if self.rule_type == 'Allow':
                cmd = f"ufw allow from {self.ip_address}"
                if self.port != 'any':
                    cmd += f" to any port {self.port}"
                if self.protocol != 'any':
                    cmd += f" proto {self.protocol}"
            else:  # Deny
                cmd = f"ufw deny from {self.ip_address}"
                if self.port != 'any':
                    cmd += f" to any port {self.port}"
            
            subprocess.run(f"sudo {cmd}", shell=True, check=True)
            
        except Exception as e:
            frappe.log_error(f"Firewall rule apply failed: {str(e)}")
    
    def remove_rule(self):
        """Remove UFW firewall rule"""
        try:
            cmd = f"ufw delete {self.rule_type.lower()} from {self.ip_address}"
            subprocess.run(f"sudo {cmd}", shell=True, check=True)
        except Exception as e:
            frappe.log_error(f"Firewall rule remove failed: {str(e)}")


@frappe.whitelist()
def get_firewall_status():
    """Get UFW firewall status"""
    try:
        result = subprocess.run(['sudo', 'ufw', 'status', 'verbose'], capture_output=True, text=True)
        return {'success': True, 'status': result.stdout}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def enable_firewall():
    """Enable UFW firewall"""
    try:
        subprocess.run(['sudo', 'ufw', '--force', 'enable'], check=True)
        return {'success': True, 'message': 'Firewall enabled'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def disable_firewall():
    """Disable UFW firewall"""
    try:
        subprocess.run(['sudo', 'ufw', 'disable'], check=True)
        return {'success': True, 'message': 'Firewall disabled'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
