# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
from datetime import datetime

class DNSZone(Document):
    def validate(self):
        """Validate DNS zone"""
        if self.cloudflare_enabled and not self.cloudflare_zone_id:
            # Try to get zone ID from Cloudflare
            self.sync_with_cloudflare()
    
    def on_update(self):
        """Sync with Cloudflare after update if enabled"""
        if self.cloudflare_enabled:
            self.push_to_cloudflare()
    
    def sync_with_cloudflare(self):
        """Sync DNS zone with Cloudflare"""
        settings = frappe.get_single('Hosting Settings')
        cf_api_key = settings.get('cloudflare_api_key')
        cf_email = settings.get('cloudflare_email')
        
        if not cf_api_key or not cf_email:
            frappe.throw("Cloudflare API credentials not configured in Hosting Settings")
        
        # Get zone ID
        zone_id = self.get_cloudflare_zone_id(cf_api_key, cf_email)
        if zone_id:
            self.db_set('cloudflare_zone_id', zone_id)
            
            # Pull existing records from Cloudflare
            self.pull_from_cloudflare()
            self.db_set('last_sync', datetime.now())
            frappe.db.commit()
    
    def get_cloudflare_zone_id(self, api_key, email):
        """Get Cloudflare zone ID for domain"""
        headers = {
            'X-Auth-Email': email,
            'X-Auth-Key': api_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'https://api.cloudflare.com/client/v4/zones?name={self.zone_name}',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['result']:
                return data['result'][0]['id']
        
        return None
    
    def pull_from_cloudflare(self):
        """Pull DNS records from Cloudflare"""
        settings = frappe.get_single('Hosting Settings')
        cf_api_key = settings.get('cloudflare_api_key')
        cf_email = settings.get('cloudflare_email')
        
        if not self.cloudflare_zone_id:
            return
        
        headers = {
            'X-Auth-Email': cf_email,
            'X-Auth-Key': cf_api_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/dns_records',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Clear existing records
            self.dns_records = []
            
            # Add records from Cloudflare
            for record in data['result']:
                self.append('dns_records', {
                    'record_type': record['type'],
                    'name_field': record['name'],
                    'value': record['content'],
                    'ttl': record['ttl'],
                    'priority': record.get('priority', 0),
                    'proxied': record.get('proxied', False)
                })
    
    def push_to_cloudflare(self):
        """Push DNS records to Cloudflare"""
        if not self.cloudflare_enabled or not self.cloudflare_zone_id:
            return
        
        settings = frappe.get_single('Hosting Settings')
        cf_api_key = settings.get('cloudflare_api_key')
        cf_email = settings.get('cloudflare_email')
        
        headers = {
            'X-Auth-Email': cf_email,
            'X-Auth-Key': cf_api_key,
            'Content-Type': 'application/json'
        }
        
        # Get existing records from Cloudflare
        response = requests.get(
            f'https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/dns_records',
            headers=headers
        )
        
        existing_records = {}
        if response.status_code == 200:
            for record in response.json()['result']:
                key = f"{record['type']}-{record['name']}"
                existing_records[key] = record['id']
        
        # Update or create records
        for record in self.dns_records:
            key = f"{record.record_type}-{record.name_field}"
            
            record_data = {
                'type': record.record_type,
                'name': record.name_field,
                'content': record.value,
                'ttl': record.ttl or 3600,
                'proxied': record.proxied or False
            }
            
            if record.record_type == 'MX' and record.priority:
                record_data['priority'] = record.priority
            
            if key in existing_records:
                # Update existing record
                requests.put(
                    f'https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/dns_records/{existing_records[key]}',
                    headers=headers,
                    json=record_data
                )
            else:
                # Create new record
                requests.post(
                    f'https://api.cloudflare.com/client/v4/zones/{self.cloudflare_zone_id}/dns_records',
                    headers=headers,
                    json=record_data
                )
        
        self.db_set('last_sync', datetime.now())


@frappe.whitelist()
def create_dns_record(zone_name, record_type, name, value, ttl=3600, priority=None, proxied=False):
    """Create a new DNS record"""
    zone = frappe.get_doc('DNS Zone', zone_name)
    
    zone.append('dns_records', {
        'record_type': record_type,
        'name_field': name,
        'value': value,
        'ttl': ttl,
        'priority': priority,
        'proxied': proxied
    })
    
    zone.save()
    
    return {'success': True, 'zone': zone_name}


@frappe.whitelist()
def delete_dns_record(zone_name, record_index):
    """Delete a DNS record"""
    zone = frappe.get_doc('DNS Zone', zone_name)
    
    if 0 <= record_index < len(zone.dns_records):
        zone.dns_records.pop(record_index)
        zone.save()
        return {'success': True}
    
    return {'success': False, 'error': 'Invalid record index'}


@frappe.whitelist()
def sync_with_cloudflare(zone_name):
    """Manually sync DNS zone with Cloudflare"""
    zone = frappe.get_doc('DNS Zone', zone_name)
    zone.sync_with_cloudflare()
    return {'success': True, 'last_sync': zone.last_sync}


@frappe.whitelist()
def check_dns_propagation(domain, record_type='A'):
    """Check DNS propagation status"""
    import dns.resolver
    
    try:
        answers = dns.resolver.resolve(domain, record_type)
        records = [str(rdata) for rdata in answers]
        
        return {
            'success': True,
            'propagated': True,
            'records': records
        }
    except Exception as e:
        return {
            'success': True,
            'propagated': False,
            'error': str(e)
        }


@frappe.whitelist()
def get_common_records():
    """Get common DNS record templates"""
    return [
        {
            'name': 'Root A Record',
            'record_type': 'A',
            'name_field': '@',
            'value': '0.0.0.0',
            'ttl': 3600,
            'description': 'Point root domain to IP address'
        },
        {
            'name': 'WWW CNAME',
            'record_type': 'CNAME',
            'name_field': 'www',
            'value': '@',
            'ttl': 3600,
            'description': 'Redirect www to root domain'
        },
        {
            'name': 'Mail MX Record',
            'record_type': 'MX',
            'name_field': '@',
            'value': 'mail.example.com',
            'ttl': 3600,
            'priority': 10,
            'description': 'Mail server record'
        },
        {
            'name': 'SPF Record',
            'record_type': 'TXT',
            'name_field': '@',
            'value': 'v=spf1 include:_spf.example.com ~all',
            'ttl': 3600,
            'description': 'Email authentication'
        },
        {
            'name': 'DKIM Record',
            'record_type': 'TXT',
            'name_field': 'default._domainkey',
            'value': 'v=DKIM1; k=rsa; p=...',
            'ttl': 3600,
            'description': 'Email signature verification'
        }
    ]
