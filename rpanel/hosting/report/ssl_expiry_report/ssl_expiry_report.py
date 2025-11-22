# Copyright (c) 2025, ROKCT Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

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
            "fieldname": "ssl_status",
            "label": _("SSL Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "ssl_issuer",
            "label": _("SSL Issuer"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "ssl_expiry_date",
            "label": _("Expiry Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "days_until_expiry",
            "label": _("Days Until Expiry"),
            "fieldtype": "Int",
            "width": 130
        },
        {
            "fieldname": "status",
            "label": _("Site Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "site_path",
            "label": _("Site Path"),
            "fieldtype": "Data",
            "width": 200
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    # Get all websites with SSL
    websites = frappe.db.sql(f"""
        SELECT 
            name as domain,
            ssl_status,
            ssl_issuer,
            ssl_expiry_date,
            status,
            site_path,
            DATEDIFF(ssl_expiry_date, CURDATE()) as days_until_expiry
        FROM 
            `tabHosted Website`
        WHERE 
            ssl_status = 'Active'
            {conditions}
        ORDER BY 
            days_until_expiry ASC
    """, as_dict=1)
    
    return websites

def get_conditions(filters):
    conditions = ""
    
    if filters.get("domain"):
        conditions += f" AND name LIKE '%{filters.get('domain')}%'"
    
    if filters.get("expiring_within_days"):
        days = filters.get("expiring_within_days")
        conditions += f" AND DATEDIFF(ssl_expiry_date, CURDATE()) <= {days}"
    
    if filters.get("status"):
        conditions += f" AND status = '{filters.get('status')}'"
    
    return conditions
