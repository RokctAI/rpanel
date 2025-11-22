# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import subprocess
import os
from datetime import datetime

@frappe.whitelist()
def scan_for_malware(website_name):
    """Scan website for malware using ClamAV"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        # Run ClamAV scan
        cmd = f"clamscan -r --infected --remove=no {website.site_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        
        # Parse results
        threats_found = 0
        if 'Infected files:' in result.stdout:
            threats_found = int(result.stdout.split('Infected files:')[1].split('\n')[0].strip())
        
        # Log scan results
        frappe.get_doc({
            'doctype': 'Security Scan',
            'website': website_name,
            'scan_date': datetime.now(),
            'threats_found': threats_found,
            'scan_results': result.stdout,
            'status': 'Clean' if threats_found == 0 else 'Threats Found'
        }).insert()
        frappe.db.commit()
        
        return {
            'success': True,
            'threats_found': threats_found,
            'results': result.stdout
        }
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Scan timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def setup_fail2ban():
    """Setup Fail2Ban for brute force protection"""
    try:
        # Check if Fail2Ban is installed
        result = subprocess.run(['which', 'fail2ban-client'], capture_output=True)
        if result.returncode != 0:
            return {'success': False, 'error': 'Fail2Ban not installed'}
        
        # Create Nginx jail configuration
        jail_config = """
[nginx-limit-req]
enabled = true
filter = nginx-limit-req
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /var/log/nginx/*error.log
findtime = 600
bantime = 7200
maxretry = 10

[nginx-noscript]
enabled = true
port = http,https
filter = nginx-noscript
logpath = /var/log/nginx/*access.log
maxretry = 6
bantime = 86400

[nginx-badbots]
enabled = true
port = http,https
filter = nginx-badbots
logpath = /var/log/nginx/*access.log
maxretry = 2
bantime = 86400
"""
        
        # Write jail configuration
        with open('/etc/fail2ban/jail.d/nginx.conf', 'w') as f:
            f.write(jail_config)
        
        # Restart Fail2Ban
        subprocess.run(['systemctl', 'restart', 'fail2ban'], check=True)
        
        return {'success': True, 'message': 'Fail2Ban configured'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_fail2ban_status():
    """Get Fail2Ban status"""
    try:
        result = subprocess.run(['fail2ban-client', 'status'], capture_output=True, text=True)
        return {'success': True, 'status': result.stdout}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def block_ip(ip_address, duration=3600):
    """Manually block IP address"""
    try:
        # Add to UFW
        subprocess.run(f"sudo ufw deny from {ip_address}", shell=True, check=True)
        
        # Log the block
        frappe.get_doc({
            'doctype': 'Security Audit Log',
            'event_type': 'IP Blocked',
            'ip_address': ip_address,
            'details': f'Manually blocked for {duration} seconds',
            'timestamp': datetime.now()
        }).insert()
        frappe.db.commit()
        
        return {'success': True, 'message': f'IP {ip_address} blocked'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def unblock_ip(ip_address):
    """Unblock IP address"""
    try:
        subprocess.run(f"sudo ufw delete deny from {ip_address}", shell=True, check=True)
        
        frappe.get_doc({
            'doctype': 'Security Audit Log',
            'event_type': 'IP Unblocked',
            'ip_address': ip_address,
            'timestamp': datetime.now()
        }).insert()
        frappe.db.commit()
        
        return {'success': True, 'message': f'IP {ip_address} unblocked'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_security_logs(limit=100):
    """Get security audit logs"""
    try:
        logs = frappe.get_all(
            'Security Audit Log',
            fields=['event_type', 'ip_address', 'details', 'timestamp'],
            order_by='timestamp desc',
            limit=limit
        )
        return {'success': True, 'logs': logs}
    except Exception as e:
        return {'success': False, 'error': str(e)}
