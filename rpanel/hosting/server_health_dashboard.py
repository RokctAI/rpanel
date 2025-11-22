# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime, timedelta

@frappe.whitelist()
def get_server_health_dashboard():
    """Get comprehensive server health dashboard data"""
    
    # Get all servers
    servers = frappe.get_all(
        'Hosting Server',
        fields=['name', 'server_name', 'server_ip', 'server_group', 'status', 
                'current_websites', 'max_websites', 'cpu_cores', 'ram_gb', 
                'disk_gb', 'health_status', 'last_health_check']
    )
    
    dashboard_data = {
        'servers': [],
        'summary': {
            'total_servers': len(servers),
            'active_servers': 0,
            'total_websites': 0,
            'total_capacity': 0,
            'healthy_servers': 0,
            'unhealthy_servers': 0
        },
        'groups': {}
    }
    
    for server in servers:
        # Get real-time resources if possible
        try:
            from rpanel.hosting.doctype.hosting_server.hosting_server import get_server_resources
            resources = get_server_resources(server.name)
            if resources.get('success'):
                server['cpu_usage'] = resources.get('cpu_usage', 'N/A')
                server['memory_usage'] = resources.get('memory_usage', 'N/A')
                server['disk_usage'] = resources.get('disk_usage', 'N/A')
        except:
            server['cpu_usage'] = 'N/A'
            server['memory_usage'] = 'N/A'
            server['disk_usage'] = 'N/A'
        
        # Calculate utilization percentage
        if server.max_websites > 0:
            server['utilization'] = round((server.current_websites / server.max_websites) * 100, 1)
        else:
            server['utilization'] = 0
        
        # Add to dashboard
        dashboard_data['servers'].append(server)
        
        # Update summary
        if server.status == 'Active':
            dashboard_data['summary']['active_servers'] += 1
        
        dashboard_data['summary']['total_websites'] += server.current_websites
        dashboard_data['summary']['total_capacity'] += server.max_websites
        
        if server.health_status == 'Healthy':
            dashboard_data['summary']['healthy_servers'] += 1
        else:
            dashboard_data['summary']['unhealthy_servers'] += 1
        
        # Group by server_group
        if server.server_group not in dashboard_data['groups']:
            dashboard_data['groups'][server.server_group] = {
                'servers': 0,
                'websites': 0,
                'capacity': 0
            }
        
        dashboard_data['groups'][server.server_group]['servers'] += 1
        dashboard_data['groups'][server.server_group]['websites'] += server.current_websites
        dashboard_data['groups'][server.server_group]['capacity'] += server.max_websites
    
    # Calculate overall utilization
    if dashboard_data['summary']['total_capacity'] > 0:
        dashboard_data['summary']['overall_utilization'] = round(
            (dashboard_data['summary']['total_websites'] / dashboard_data['summary']['total_capacity']) * 100, 1
        )
    else:
        dashboard_data['summary']['overall_utilization'] = 0
    
    return {'success': True, 'dashboard': dashboard_data}


@frappe.whitelist()
def get_server_alerts():
    """Get server alerts and warnings"""
    alerts = []
    
    # Check for unhealthy servers
    unhealthy = frappe.get_all(
        'Hosting Server',
        filters={'health_status': ['!=', 'Healthy']},
        fields=['server_name', 'health_status', 'last_health_check']
    )
    
    for server in unhealthy:
        alerts.append({
            'type': 'error',
            'server': server.server_name,
            'message': f"Server is {server.health_status}",
            'timestamp': server.last_health_check
        })
    
    # Check for servers near capacity
    near_capacity = frappe.db.sql("""
        SELECT server_name, current_websites, max_websites
        FROM `tabHosting Server`
        WHERE current_websites >= max_websites * 0.9
        AND status = 'Active'
    """, as_dict=True)
    
    for server in near_capacity:
        alerts.append({
            'type': 'warning',
            'server': server.server_name,
            'message': f"Near capacity: {server.current_websites}/{server.max_websites} websites",
            'timestamp': datetime.now()
        })
    
    # Check for servers not checked recently
    stale_threshold = datetime.now() - timedelta(hours=1)
    stale_servers = frappe.get_all(
        'Hosting Server',
        filters=[
            ['last_health_check', '<', stale_threshold],
            ['status', '=', 'Active']
        ],
        fields=['server_name', 'last_health_check']
    )
    
    for server in stale_servers:
        alerts.append({
            'type': 'warning',
            'server': server.server_name,
            'message': 'Health check overdue',
            'timestamp': server.last_health_check
        })
    
    return {'success': True, 'alerts': alerts}


@frappe.whitelist()
def get_server_performance_history(server_name, days=7):
    """Get server performance history"""
    # This would query resource usage logs
    # For now, return placeholder
    return {
        'success': True,
        'history': {
            'cpu': [],
            'memory': [],
            'disk': [],
            'websites': []
        }
    }
