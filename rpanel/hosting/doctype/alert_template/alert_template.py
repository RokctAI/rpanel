# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
import re

class AlertTemplate(Document):
    def validate(self):
        """Validate template variables"""
        if not self.variables:
            self.set_default_variables()
    
    def set_default_variables(self):
        """Set default variables based on category"""
        variables = {
            'SSL Expiry': {
                'domain': 'Website domain',
                'days_left': 'Days until expiry',
                'expiry_date': 'SSL expiry date',
                'ssl_issuer': 'Certificate issuer'
            },
            'Disk Space': {
                'domain': 'Website domain',
                'disk_usage': 'Current disk usage in MB',
                'disk_limit': 'Disk limit in MB',
                'percentage': 'Usage percentage'
            },
            'CPU Usage': {
                'domain': 'Website domain',
                'cpu_usage': 'Current CPU usage percentage',
                'threshold': 'Alert threshold',
                'duration': 'Duration of high usage'
            },
            'Uptime Alert': {
                'domain': 'Website domain',
                'status': 'Current status',
                'downtime_duration': 'Downtime duration',
                'error_message': 'Error details'
            }
        }
        
        self.variables = json.dumps(variables.get(self.category, {}), indent=2)


@frappe.whitelist()
def send_alert_email(template_name, recipient, variables_dict):
    """Send alert email using template"""
    template = frappe.get_doc('Alert Template', template_name)
    
    if not template.enabled:
        return {'success': False, 'error': 'Template is disabled'}
    
    # Parse variables
    if isinstance(variables_dict, str):
        variables_dict = json.loads(variables_dict)
    
    # Replace variables in subject and body
    subject = replace_variables(template.subject, variables_dict)
    body = replace_variables(template.body, variables_dict)
    
    try:
        frappe.sendmail(
            recipients=recipient,
            subject=subject,
            message=body,
            delayed=False
        )
        
        return {'success': True, 'message': 'Alert sent'}
        
    except Exception as e:
        frappe.log_error(f"Alert email failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def preview_template(template_name, sample_data=None):
    """Preview template with sample data"""
    template = frappe.get_doc('Alert Template', template_name)
    
    # Use provided sample data or template's sample data
    if sample_data:
        data = json.loads(sample_data) if isinstance(sample_data, str) else sample_data
    elif template.sample_data:
        data = json.loads(template.sample_data)
    else:
        # Use default sample data
        data = get_default_sample_data(template.category)
    
    subject = replace_variables(template.subject, data)
    body = replace_variables(template.body, data)
    
    return {
        'success': True,
        'subject': subject,
        'body': body
    }


@frappe.whitelist()
def get_template_by_category(category):
    """Get active template for category"""
    templates = frappe.get_all(
        'Alert Template',
        filters={'category': category, 'enabled': 1},
        fields=['name', 'template_name', 'subject'],
        limit=1
    )
    
    return templates[0] if templates else None


def replace_variables(text, variables):
    """Replace {variable} placeholders with actual values"""
    for key, value in variables.items():
        text = text.replace(f'{{{key}}}', str(value))
    return text


def get_default_sample_data(category):
    """Get default sample data for preview"""
    samples = {
        'SSL Expiry': {
            'domain': 'example.com',
            'days_left': '7',
            'expiry_date': '2025-12-01',
            'ssl_issuer': "Let's Encrypt"
        },
        'Disk Space': {
            'domain': 'example.com',
            'disk_usage': '850',
            'disk_limit': '1000',
            'percentage': '85'
        },
        'CPU Usage': {
            'domain': 'example.com',
            'cpu_usage': '95',
            'threshold': '80',
            'duration': '15 minutes'
        }
    }
    
    return samples.get(category, {})


@frappe.whitelist()
def create_default_templates():
    """Create default alert templates"""
    templates = [
        {
            'template_name': 'SSL Expiry Warning',
            'category': 'SSL Expiry',
            'subject': 'SSL Certificate Expiring Soon - {domain}',
            'body': '''
                <h3>SSL Certificate Expiring Soon</h3>
                <p>The SSL certificate for <strong>{domain}</strong> will expire in <strong>{days_left} days</strong>.</p>
                <p><strong>Expiry Date:</strong> {expiry_date}</p>
                <p><strong>Issuer:</strong> {ssl_issuer}</p>
                <p>Please renew the certificate to avoid service interruption.</p>
            ''',
            'enabled': 1,
            'priority': 'High'
        },
        {
            'template_name': 'Disk Space Alert',
            'category': 'Disk Space',
            'subject': 'Disk Space Alert - {domain}',
            'body': '''
                <h3>Disk Space Alert</h3>
                <p>The website <strong>{domain}</strong> is using <strong>{percentage}%</strong> of allocated disk space.</p>
                <p><strong>Current Usage:</strong> {disk_usage} MB</p>
                <p><strong>Limit:</strong> {disk_limit} MB</p>
                <p>Please review and clean up unnecessary files.</p>
            ''',
            'enabled': 1,
            'priority': 'Medium'
        }
    ]
    
    created = []
    for tmpl in templates:
        if not frappe.db.exists('Alert Template', tmpl['template_name']):
            doc = frappe.get_doc({
                'doctype': 'Alert Template',
                **tmpl
            })
            doc.insert()
            created.append(tmpl['template_name'])
    
    return {'success': True, 'created': created}
