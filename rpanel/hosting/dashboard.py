# Copyright (c) 2025, ROKCT Holdings and contributors
# For license information, please see license.txt

import frappe

@frappe.whitelist()
def get_hosting_dashboard_data():
    """Get dashboard metrics for hosting workspace"""
    
    # Total websites
    total_websites = frappe.db.count('Hosted Website')
    
    # Active websites
    active_websites = frappe.db.count('Hosted Website', {'status': 'Active'})
    
    # SSL enabled sites
    ssl_enabled = frappe.db.count('Hosted Website', {'ssl_status': 'Active'})
    
    # WordPress sites
    wordpress_sites = frappe.db.count('Hosted Website', {
        'site_type': 'CMS',
        'cms_type': 'WordPress'
    })
    
    # SSL expiring soon (within 30 days)
    # This would require checking ssl_expiry_date field if it exists
    # For now, we'll return 0 as placeholder
    ssl_expiring = 0
    
    # Pending sites
    pending_sites = frappe.db.count('Hosted Website', {'status': 'Pending'})
    
    # Total email accounts
    total_emails = frappe.db.sql("""
        SELECT COUNT(*) 
        FROM `tabHosted Email Account`
    """)[0][0] if frappe.db.exists('DocType', 'Hosted Email Account') else 0
    
    return {
        'total_websites': total_websites,
        'active_websites': active_websites,
        'ssl_enabled': ssl_enabled,
        'wordpress_sites': wordpress_sites,
        'ssl_expiring': ssl_expiring,
        'pending_sites': pending_sites,
        'total_emails': total_emails
    }

@frappe.whitelist()
def get_recent_websites(limit=5):
    """Get recently created websites"""
    websites = frappe.get_all(
        'Hosted Website',
        fields=['name', 'domain', 'status', 'ssl_status', 'creation'],
        order_by='creation desc',
        limit=limit
    )
    return websites
