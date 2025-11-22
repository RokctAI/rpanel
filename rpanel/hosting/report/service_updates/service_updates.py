# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns = [
        {
            "fieldname": "service_name",
            "label": "Service",
            "fieldtype": "Link",
            "options": "Service Version",
            "width": 150
        },
        {
            "fieldname": "service_type",
            "label": "Type",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "server",
            "label": "Server",
            "fieldtype": "Link",
            "options": "Hosting Server",
            "width": 150
        },
        {
            "fieldname": "current_version",
            "label": "Current Version",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "fieldname": "latest_version",
            "label": "Latest Version",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "fieldname": "update_available",
            "label": "Update Available",
            "fieldtype": "Check",
            "width": 120
        },
        {
            "fieldname": "last_checked",
            "label": "Last Checked",
            "fieldtype": "Datetime",
            "width": 150
        }
    ]
    
    data = frappe.get_all(
        'Service Version',
        filters=filters or {},
        fields=['name as service_name', 'service_type', 'server', 'current_version', 'latest_version', 'update_available', 'last_checked'],
        order_by='update_available desc, service_type asc'
    )
    
    return columns, data
