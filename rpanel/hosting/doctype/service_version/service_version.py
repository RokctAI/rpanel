# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import subprocess
import re
from datetime import datetime

class ServiceVersion(Document):
    pass

@frappe.whitelist()
def check_service_updates(server_name=None):
    """
    Check for updates for all services on a server or all servers
    """
    filters = {}
    if server_name:
        filters['server'] = server_name
    
    services = frappe.get_all('Service Version', filters=filters, fields=['name', 'service_type', 'server'])
    
    for service in services:
        doc = frappe.get_doc('Service Version', service.name)
        _check_version(doc)
        doc.save()
    
    frappe.db.commit()
    return {"success": True, "message": f"Checked {len(services)} services"}

def _check_version(doc):
    """Check current and latest version for a service"""
    from rpanel.hosting.doctype.hosting_server.hosting_server import execute_remote_command
    
    server_name = doc.server
    service_type = doc.service_type
    
    # Commands to check versions
    version_commands = {
        'PHP': "php -v | head -n 1 | awk '{print $2}'",
        'Nginx': "nginx -v 2>&1 | awk -F'/' '{print $2}'",
        'MariaDB': "mysql --version | awk '{print $5}' | sed 's/,//'",
        'WordPress': "wp core version --allow-root 2>/dev/null || echo 'Not installed'",
        'Roundcube': "dpkg -l | grep roundcube-core | awk '{print $3}'",
        'phpMyAdmin': "dpkg -l | grep phpmyadmin | awk '{print $3}'",
        'ClamAV': "clamscan --version | awk '{print $2}' | sed 's/\\/.*$//'",
        'Fail2Ban': "fail2ban-client version",
        'Certbot': "certbot --version | awk '{print $2}'",
        'Exim4': "exim4 --version | head -n 1 | awk '{print $3}'",
        'Dovecot': "dovecot --version | awk '{print $1}'"
    }
    
    # Commands to check latest available version
    latest_commands = {
        'PHP': "apt-cache policy php8.3 | grep Candidate | awk '{print $2}'",
        'Nginx': "apt-cache policy nginx | grep Candidate | awk '{print $2}'",
        'MariaDB': "apt-cache policy mariadb-server | grep Candidate | awk '{print $2}'",
        'WordPress': "curl -s https://api.wordpress.org/core/version-check/1.7/ | jq -r '.offers[0].version'",
        'Roundcube': "apt-cache policy roundcube-core | grep Candidate | awk '{print $2}'",
        'phpMyAdmin': "apt-cache policy phpmyadmin | grep Candidate | awk '{print $2}'",
        'ClamAV': "apt-cache policy clamav | grep Candidate | awk '{print $2}'",
        'Fail2Ban': "apt-cache policy fail2ban | grep Candidate | awk '{print $2}'",
        'Certbot': "apt-cache policy certbot | grep Candidate | awk '{print $2}'",
        'Exim4': "apt-cache policy exim4 | grep Candidate | awk '{print $2}'",
        'Dovecot': "apt-cache policy dovecot-core | grep Candidate | awk '{print $2}'"
    }
    
    if service_type in version_commands:
        # Get current version
        result = execute_remote_command(server_name, version_commands[service_type])
        if result.get('success'):
            current_version = result.get('output', '').strip()
            doc.current_version = current_version
        
        # Get latest version
        result = execute_remote_command(server_name, latest_commands[service_type])
        if result.get('success'):
            latest_version = result.get('output', '').strip()
            doc.latest_version = latest_version
            
            # Check if update available
            if current_version and latest_version and current_version != latest_version:
                doc.update_available = 1
            else:
                doc.update_available = 0
    
    doc.last_checked = datetime.now()

@frappe.whitelist()
def update_service(service_name):
    """
    Update a specific service to the latest version
    """
    doc = frappe.get_doc('Service Version', service_name)
    from rpanel.hosting.doctype.hosting_server.hosting_server import execute_remote_command
    
    service_type = doc.service_type
    server_name = doc.server
    
    # Update commands
    update_commands = {
        'PHP': "apt-get update && apt-get install --only-upgrade -y php8.3-fpm php8.3-mysql php8.3-curl php8.3-gd php8.3-mbstring php8.3-xml php8.3-zip && systemctl restart php8.3-fpm",
        'Nginx': "apt-get update && apt-get install --only-upgrade -y nginx && systemctl restart nginx",
        'MariaDB': "apt-get update && apt-get install --only-upgrade -y mariadb-server mariadb-client && systemctl restart mariadb",
        'WordPress': "wp core update --allow-root",
        'Roundcube': "apt-get update && apt-get install --only-upgrade -y roundcube roundcube-core roundcube-mysql",
        'phpMyAdmin': "apt-get update && apt-get install --only-upgrade -y phpmyadmin",
        'ClamAV': "apt-get update && apt-get install --only-upgrade -y clamav clamav-daemon && systemctl restart clamav-daemon",
        'Fail2Ban': "apt-get update && apt-get install --only-upgrade -y fail2ban && systemctl restart fail2ban",
        'Certbot': "apt-get update && apt-get install --only-upgrade -y certbot python3-certbot-nginx",
        'Exim4': "apt-get update && apt-get install --only-upgrade -y exim4 exim4-daemon-heavy && systemctl restart exim4",
        'Dovecot': "apt-get update && apt-get install --only-upgrade -y dovecot-core dovecot-imapd dovecot-pop3d && systemctl restart dovecot"
    }
    
    if service_type in update_commands:
        result = execute_remote_command(server_name, update_commands[service_type], timeout=600)
        
        if result.get('success'):
            # Re-check version after update
            _check_version(doc)
            doc.save()
            frappe.db.commit()
            
            return {
                "success": True,
                "message": f"{service_type} updated successfully to {doc.current_version}",
                "new_version": doc.current_version
            }
        else:
            return {
                "success": False,
                "error": result.get('error', 'Update failed')
            }
    else:
        return {
            "success": False,
            "error": f"Update not supported for {service_type}"
        }
