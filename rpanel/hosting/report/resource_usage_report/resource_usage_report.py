# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart_data(data, filters)
    
    return columns, data, None, chart


def get_columns():
    return [
        {
            'fieldname': 'website',
            'label': _('Website'),
            'fieldtype': 'Link',
            'options': 'Hosted Website',
            'width': 200
        },
        {
            'fieldname': 'timestamp',
            'label': _('Timestamp'),
            'fieldtype': 'Datetime',
            'width': 150
        },
        {
            'fieldname': 'cpu_usage',
            'label': _('CPU (%)'),
            'fieldtype': 'Float',
            'width': 100,
            'precision': 2
        },
        {
            'fieldname': 'memory_usage',
            'label': _('Memory (MB)'),
            'fieldtype': 'Float',
            'width': 120,
            'precision': 2
        },
        {
            'fieldname': 'disk_usage',
            'label': _('Disk (MB)'),
            'fieldtype': 'Float',
            'width': 120,
            'precision': 2
        },
        {
            'fieldname': 'bandwidth_in',
            'label': _('Bandwidth In (MB)'),
            'fieldtype': 'Float',
            'width': 150,
            'precision': 2
        },
        {
            'fieldname': 'bandwidth_out',
            'label': _('Bandwidth Out (MB)'),
            'fieldtype': 'Float',
            'width': 150,
            'precision': 2
        },
        {
            'fieldname': 'request_count',
            'label': _('Requests'),
            'fieldtype': 'Int',
            'width': 100
        },
        {
            'fieldname': 'error_count',
            'label': _('Errors'),
            'fieldtype': 'Int',
            'width': 100
        }
    ]


def get_data(filters):
    conditions = []
    
    if filters.get('website'):
        conditions.append(f"website = '{filters.get('website')}'")
    
    if filters.get('from_date'):
        conditions.append(f"timestamp >= '{filters.get('from_date')}'")
    
    if filters.get('to_date'):
        conditions.append(f"timestamp <= '{filters.get('to_date')}'")
    
    where_clause = ' AND '.join(conditions) if conditions else '1=1'
    
    data = frappe.db.sql(f"""
        SELECT
            website,
            timestamp,
            cpu_usage,
            memory_usage,
            disk_usage,
            bandwidth_in,
            bandwidth_out,
            request_count,
            error_count
        FROM `tabResource Usage Log`
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT 1000
    """, as_dict=1)
    
    return data


def get_chart_data(data, filters):
    if not data:
        return None
    
    # Group by hour for better visualization
    hourly_data = {}
    
    for row in data:
        hour = row.timestamp.strftime('%Y-%m-%d %H:00')
        if hour not in hourly_data:
            hourly_data[hour] = {
                'cpu': [],
                'memory': [],
                'disk': [],
                'requests': 0,
                'errors': 0
            }
        
        hourly_data[hour]['cpu'].append(row.cpu_usage or 0)
        hourly_data[hour]['memory'].append(row.memory_usage or 0)
        hourly_data[hour]['disk'].append(row.disk_usage or 0)
        hourly_data[hour]['requests'] += row.request_count or 0
        hourly_data[hour]['errors'] += row.error_count or 0
    
    # Calculate averages
    labels = sorted(hourly_data.keys())
    cpu_values = [sum(hourly_data[h]['cpu']) / len(hourly_data[h]['cpu']) if hourly_data[h]['cpu'] else 0 for h in labels]
    memory_values = [sum(hourly_data[h]['memory']) / len(hourly_data[h]['memory']) if hourly_data[h]['memory'] else 0 for h in labels]
    
    chart = {
        'data': {
            'labels': labels[-24:],  # Last 24 hours
            'datasets': [
                {
                    'name': 'CPU Usage (%)',
                    'values': cpu_values[-24:]
                },
                {
                    'name': 'Memory Usage (MB)',
                    'values': memory_values[-24:]
                }
            ]
        },
        'type': 'line',
        'colors': ['#4CAF50', '#2196F3'],
        'axisOptions': {
            'xIsSeries': 1
        }
    }
    
    return chart
