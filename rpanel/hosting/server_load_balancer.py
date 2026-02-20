# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe

@frappe.whitelist()
def get_server_by_group(group_name):
    """Get all servers in a group"""
    servers = frappe.get_all(
        'Hosting Server',
        filters={'server_group': group_name, 'status': 'Active'},
        fields=['name', 'server_name', 'server_ip', 'current_websites', 'max_websites', 'cpu_cores', 'ram_gb']
    )
    
    return {'success': True, 'servers': servers}


@frappe.whitelist()
def get_optimal_server_with_load_balancing(group='Production', algorithm='least_loaded'):  # noqa: C901
    """Get optimal server using load balancing algorithm"""
    servers = frappe.get_all(
        'Hosting Server',
        filters={'server_group': group, 'status': 'Active'},
        fields=['name', 'server_name', 'current_websites', 'max_websites', 'cpu_cores', 'ram_gb'],
        order_by='current_websites asc'
    )
    
    if not servers:
        return {'success': False, 'error': 'No available servers in group'}
    
    if algorithm == 'round_robin':
        # Round robin - get server with lowest ID that has capacity
        for server in servers:
            if server.current_websites < server.max_websites:
                return {'success': True, 'server': server.name, 'algorithm': 'round_robin'}
    
    elif algorithm == 'least_loaded':
        # Least loaded - server with lowest current_websites
        for server in servers:
            if server.current_websites < server.max_websites:
                return {'success': True, 'server': server.name, 'algorithm': 'least_loaded'}
    
    elif algorithm == 'weighted':
        # Weighted by resources (CPU cores * RAM)
        available_servers = [s for s in servers if s.current_websites < s.max_websites]
        if available_servers:
            # Calculate weight: (cpu_cores * ram_gb) / current_websites
            for server in available_servers:
                weight = (server.cpu_cores * server.ram_gb) / max(server.current_websites, 1)
                server['weight'] = weight
            
            # Sort by weight descending
            available_servers.sort(key=lambda x: x['weight'], reverse=True)
            return {'success': True, 'server': available_servers[0].name, 'algorithm': 'weighted'}
    
    return {'success': False, 'error': 'No available servers'}


@frappe.whitelist()
def distribute_websites_across_group(group_name):
    """Distribute websites evenly across server group"""
    servers = frappe.get_all(
        'Hosting Server',
        filters={'server_group': group_name, 'status': 'Active'},
        fields=['name', 'current_websites', 'max_websites']
    )
    
    if not servers:
        return {'success': False, 'error': 'No servers in group'}
    
    # Get all websites without assigned server
    unassigned_websites = frappe.get_all(
        'Hosted Website',
        filters={'server': ['is', 'not set']},
        fields=['name']
    )
    
    # Distribute using round-robin
    server_index = 0
    distributed = 0
    
    for website in unassigned_websites:
        # Find next available server
        while server_index < len(servers):
            server = servers[server_index]
            if server.current_websites < server.max_websites:
                # Assign website to server
                frappe.db.set_value('Hosted Website', website.name, 'server', server.name)
                server.current_websites += 1
                distributed += 1
                server_index = (server_index + 1) % len(servers)
                break
            server_index = (server_index + 1) % len(servers)
    
    frappe.db.commit()
    
    return {
        'success': True,
        'distributed': distributed,
        'message': f'Distributed {distributed} websites across {len(servers)} servers'
    }
