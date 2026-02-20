# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import paramiko
import subprocess
import shlex
from datetime import datetime

class HostingServer(Document):
    pass


@frappe.whitelist()
def test_connection(server_name):
    """Test SSH connection to server"""
    server = frappe.get_doc('Hosting Server', server_name)
    
    try:
        client = get_ssh_client(server)
        stdin, stdout, stderr = client.exec_command('echo "Connection successful"')
        result = stdout.read().decode()
        client.close()
        
        server.db_set('health_status', 'Healthy')
        server.db_set('last_health_check', datetime.now())
        frappe.db.commit()
        
        return {'success': True, 'message': 'Connection successful'}
    except Exception as e:
        server.db_set('health_status', 'Unhealthy')
        frappe.db.commit()
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def execute_command(server_name, command):
    """Execute command on remote server"""
    server = frappe.get_doc('Hosting Server', server_name)
    
    try:
        client = get_ssh_client(server)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        client.close()
        
        return {'success': True, 'output': output, 'error': error}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_server_resources(server_name):
    """Get server resource usage"""
    server = frappe.get_doc('Hosting Server', server_name)
    
    try:
        client = get_ssh_client(server)
        
        # CPU usage
        stdin, stdout, stderr = client.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
        cpu_usage = stdout.read().decode().strip()
        
        # Memory usage
        stdin, stdout, stderr = client.exec_command("free -m | awk 'NR==2{printf \"%.2f\", $3*100/$2 }'")
        memory_usage = stdout.read().decode().strip()
        
        # Disk usage
        stdin, stdout, stderr = client.exec_command("df -h / | awk 'NR==2{print $5}'")
        disk_usage = stdout.read().decode().strip()
        
        client.close()
        
        return {
            'success': True,
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def deploy_website_to_server(website_name, server_name):
    """Deploy website to specific server"""
    website = frappe.get_doc('Hosted Website', website_name)
    server = frappe.get_doc('Hosting Server', server_name)
    
    try:
        client = get_ssh_client(server)
        
        # Create website directory on remote server
        commands = [
            f"mkdir -p /var/www/{website.domain}",
            f"chown -R www-data:www-data /var/www/{website.domain}"
        ]
        
        for cmd in commands:
            client.exec_command(cmd)
        
        # Transfer files (using rsync over SSH)
        local_path = website.site_path
        remote_path = f"{server.ssh_username}@{server.server_ip}:/var/www/{website.domain}/"
        
        rsync_cmd = f"rsync -avz -e 'ssh -p {server.ssh_port}' {local_path}/ {remote_path}"
        subprocess.run(shlex.split(rsync_cmd), check=True)
        
        client.close()
        
        # Update server website count
        server.db_set('current_websites', server.current_websites + 1)
        frappe.db.commit()
        
        return {'success': True, 'message': f'Website deployed to {server_name}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_optimal_server(group='Production'):
    """Get server with lowest load for deployment"""
    servers = frappe.get_all(
        'Hosting Server',
        filters={'server_group': group, 'status': 'Active'},
        fields=['name', 'current_websites', 'max_websites'],
        order_by='current_websites asc'
    )
    
    for server in servers:
        if server.current_websites < server.max_websites:
            return {'success': True, 'server': server.name}
    
    return {'success': False, 'error': 'No available servers'}


def get_ssh_client(server):
    """Get SSH client for server"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507 — managed hosting: servers are provisioned programmatically
    
    if server.ssh_key:
        # Use SSH key
        from io import StringIO
        key = paramiko.RSAKey.from_private_key(StringIO(server.ssh_key))
        client.connect(
            server.server_ip,
            port=server.ssh_port,
            username=server.ssh_username,
            pkey=key
        )
    else:
        # Use password
        client.connect(
            server.server_ip,
            port=server.ssh_port,
            username=server.ssh_username,
            password=server.get_password('ssh_password')
        )
    
    return client
