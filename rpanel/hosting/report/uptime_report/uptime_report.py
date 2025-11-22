# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data, filters)
    chart = get_chart_data(data, filters)
    
    return columns, data, None, chart, summary


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
            'fieldname': 'check_time',
            'label': _('Check Time'),
            'fieldtype': 'Datetime',
            'width': 150
        },
        {
            'fieldname': 'is_up',
            'label': _('Status'),
            'fieldtype': 'Data',
            'width': 100
        },
        {
            'fieldname': 'status_code',
            'label': _('HTTP Status'),
            'fieldtype': 'Int',
            'width': 100
        },
        {
            'fieldname': 'response_time',
            'label': _('Response Time (ms)'),
            'fieldtype': 'Float',
            'width': 150,
            'precision': 2
        },
        {
            'fieldname': 'error_message',
            'label': _('Error Message'),
            'fieldtype': 'Data',
            'width': 300
        }
    ]


def get_data(filters):
    conditions = []
    
    if filters.get('website'):
        conditions.append(f"website = '{filters.get('website')}'")
    
    if filters.get('from_date'):
        conditions.append(f"check_time >= '{filters.get('from_date')}'")
    
    if filters.get('to_date'):
        conditions.append(f"check_time <= '{filters.get('to_date')}'")
    
    where_clause = ' AND '.join(conditions) if conditions else '1=1'
    
    data = frappe.db.sql(f"""
        SELECT
            website,
            check_time,
            is_up,
            status_code,
            response_time,
            error_message
        FROM `tabUptime Check`
        WHERE {where_clause}
        ORDER BY check_time DESC
        LIMIT 1000
    """, as_dict=1)
    
    # Format status
    for row in data:
        row['is_up'] = 'Up' if row.is_up else 'Down'
    
    return data


def get_summary(data, filters):
    if not data:
        return []
    
    total_checks = len(data)
    up_checks = sum(1 for d in data if d['is_up'] == 'Up')
    down_checks = total_checks - up_checks
    uptime_percentage = (up_checks / total_checks * 100) if total_checks > 0 else 0
    
    # Calculate average response time for successful checks
    response_times = [d.response_time for d in data if d['is_up'] == 'Up' and d.response_time]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    return [
        {
            'value': f"{uptime_percentage:.2f}%",
            'label': 'Uptime',
            'indicator': 'green' if uptime_percentage >= 99 else 'orange' if uptime_percentage >= 95 else 'red',
            'datatype': 'Data'
        },
        {
            'value': up_checks,
            'label': 'Successful Checks',
            'indicator': 'green',
            'datatype': 'Int'
        },
        {
            'value': down_checks,
            'label': 'Failed Checks',
            'indicator': 'red' if down_checks > 0 else 'gray',
            'datatype': 'Int'
        },
        {
            'value': f"{avg_response_time:.2f} ms",
            'label': 'Avg Response Time',
            'indicator': 'blue',
            'datatype': 'Data'
        }
    ]


def get_chart_data(data, filters):
    if not data:
        return None
    
    # Group by hour
    hourly_data = {}
    
    for row in data:
        hour = row.check_time.strftime('%Y-%m-%d %H:00')
        if hour not in hourly_data:
            hourly_data[hour] = {'up': 0, 'down': 0, 'response_times': []}
        
        if row['is_up'] == 'Up':
            hourly_data[hour]['up'] += 1
            if row.response_time:
                hourly_data[hour]['response_times'].append(row.response_time)
        else:
            hourly_data[hour]['down'] += 1
    
    labels = sorted(hourly_data.keys())
    uptime_values = [(hourly_data[h]['up'] / (hourly_data[h]['up'] + hourly_data[h]['down']) * 100) 
                     if (hourly_data[h]['up'] + hourly_data[h]['down']) > 0 else 0 
                     for h in labels]
    
    chart = {
        'data': {
            'labels': labels[-24:],  # Last 24 hours
            'datasets': [
                {
                    'name': 'Uptime (%)',
                    'values': uptime_values[-24:]
                }
            ]
        },
        'type': 'line',
        'colors': ['#4CAF50'],
        'axisOptions': {
            'xIsSeries': 1
        },
        'lineOptions': {
            'regionFill': 1
        }
    }
    
    return chart
