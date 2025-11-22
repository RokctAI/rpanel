# Copyright (c) 2025, ROKCT Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data)
    return columns, data, None, chart

def get_columns():
    return [
        {
            "fieldname": "domain",
            "label": _("Domain"),
            "fieldtype": "Link",
            "options": "Hosted Website",
            "width": 200
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "site_type",
            "label": _("Site Type"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "cms_type",
            "label": _("CMS Type"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "php_version",
            "label": _("PHP Version"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "ssl_status",
            "label": _("SSL Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "db_name",
            "label": _("Database"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "email_count",
            "label": _("Email Accounts"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "creation",
            "label": _("Created On"),
            "fieldtype": "Date",
            "width": 120
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    websites = frappe.db.sql(f"""
        SELECT 
            hw.name as domain,
            hw.status,
            hw.site_type,
            hw.cms_type,
            hw.php_version,
            hw.ssl_status,
            hw.db_name,
            hw.creation,
            (SELECT COUNT(*) FROM `tabHosted Email Account` 
             WHERE parent = hw.name) as email_count
        FROM 
            `tabHosted Website` hw
        WHERE 
            1=1
            {conditions}
        ORDER BY 
            hw.creation DESC
    """, as_dict=1)
    
    return websites

def get_conditions(filters):
    conditions = ""
    
    if filters.get("domain"):
        conditions += f" AND hw.name LIKE '%{filters.get('domain')}%'"
    
    if filters.get("status"):
        conditions += f" AND hw.status = '{filters.get('status')}'"
    
    if filters.get("site_type"):
        conditions += f" AND hw.site_type = '{filters.get('site_type')}'"
    
    if filters.get("ssl_status"):
        conditions += f" AND hw.ssl_status = '{filters.get('ssl_status')}'"
    
    if filters.get("from_date"):
        conditions += f" AND hw.creation >= '{filters.get('from_date')}'"
    
    if filters.get("to_date"):
        conditions += f" AND hw.creation <= '{filters.get('to_date')}'"
    
    return conditions

def get_chart_data(data):
    """Generate chart showing website status distribution"""
    status_count = {}
    ssl_count = {"Active": 0, "Inactive": 0}
    
    for row in data:
        # Status distribution
        status = row.get("status", "Unknown")
        status_count[status] = status_count.get(status, 0) + 1
        
        # SSL distribution
        if row.get("ssl_status") == "Active":
            ssl_count["Active"] += 1
        else:
            ssl_count["Inactive"] += 1
    
    return {
        "data": {
            "labels": list(status_count.keys()),
            "datasets": [
                {
                    "name": "Website Status",
                    "values": list(status_count.values())
                }
            ]
        },
        "type": "donut",
        "height": 250,
        "colors": ["#10B981", "#F59E0B", "#EF4444", "#6B7280"]
    }
