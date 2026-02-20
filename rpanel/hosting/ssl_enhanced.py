# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import subprocess
import shlex
import os
from datetime import datetime, timedelta

@frappe.whitelist()
def issue_wildcard_ssl(website_name):
    """Issue wildcard SSL certificate using DNS-01 challenge"""
    website = frappe.get_doc('Hosted Website', website_name)
    domain = website.domain
    
    try:
        # Use Certbot with DNS plugin (Cloudflare example)
        settings = frappe.get_single('Hosting Settings')
        cf_api_key = settings.get('cloudflare_api_key')
        
        if not cf_api_key:
            return {'success': False, 'error': 'Cloudflare API key not configured'}
        
        # Create Cloudflare credentials file
        creds_file = f"/tmp/cloudflare_{domain}.ini"
        with open(creds_file, 'w') as f:
            f.write(f"dns_cloudflare_api_token = {cf_api_key}\n")
        
        os.chmod(creds_file, 0o600)
        
        # Issue wildcard certificate
        cmd = f"certbot certonly --dns-cloudflare --dns-cloudflare-credentials {creds_file} -d {domain} -d *.{domain} --non-interactive --agree-tos --email admin@{domain}"
        result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
        
        # Clean up
        os.remove(creds_file)
        
        if result.returncode == 0:
            # Update website SSL info
            cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
            expiry = get_ssl_expiry_date(cert_path)
            
            website.db_set('ssl_status', 'Active')
            website.db_set('ssl_expiry_date', expiry)
            website.db_set('ssl_type', 'Wildcard')
            frappe.db.commit()
            
            return {'success': True, 'message': 'Wildcard SSL issued'}
        else:
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        frappe.log_error(f"Wildcard SSL failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def upload_custom_ssl(website_name, certificate, private_key, chain=None):
    """Upload custom SSL certificate"""
    website = frappe.get_doc('Hosted Website', website_name)
    domain = website.domain
    
    try:
        # Create SSL directory
        ssl_dir = f"/etc/nginx/ssl/{domain}"
        os.makedirs(ssl_dir, exist_ok=True)
        
        # Write certificate files
        cert_file = f"{ssl_dir}/certificate.crt"
        key_file = f"{ssl_dir}/private.key"
        
        with open(cert_file, 'w') as f:
            f.write(certificate)
        
        with open(key_file, 'w') as f:
            f.write(private_key)
        
        if chain:
            chain_file = f"{ssl_dir}/chain.crt"
            with open(chain_file, 'w') as f:
                f.write(chain)
        
        # Set permissions
        os.chmod(key_file, 0o600)
        
        # Update Nginx config to use custom SSL
        update_nginx_ssl_config(domain, cert_file, key_file)
        
        # Get expiry date
        expiry = get_ssl_expiry_date(cert_file)
        
        # Update website
        website.db_set('ssl_status', 'Active')
        website.db_set('ssl_expiry_date', expiry)
        website.db_set('ssl_type', 'Custom')
        frappe.db.commit()
        
        return {'success': True, 'message': 'Custom SSL uploaded'}
        
    except Exception as e:
        frappe.log_error(f"Custom SSL upload failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def check_ssl_health(website_name):
    """Check SSL certificate health"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        import ssl
        import socket
        from datetime import datetime
        
        context = ssl.create_default_context()
        
        with socket.create_connection((website.domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=website.domain) as ssock:
                cert = ssock.getpeercert()
                
                # Parse expiry date
                expiry_str = cert['notAfter']
                expiry_date = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z')
                days_left = (expiry_date - datetime.now()).days
                
                # Check certificate chain
                chain_valid = True  # Simplified check
                
                # Check common name
                subject = dict(x[0] for x in cert['subject'])
                common_name = subject.get('commonName', '')
                
                return {
                    'success': True,
                    'expiry_date': expiry_date.strftime('%Y-%m-%d'),
                    'days_left': days_left,
                    'chain_valid': chain_valid,
                    'common_name': common_name,
                    'issuer': dict(x[0] for x in cert['issuer']).get('organizationName', 'Unknown')
                }
                
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def renew_ssl_certificate(website_name):
    """Renew SSL certificate"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        if website.ssl_type == 'Wildcard':
            return issue_wildcard_ssl(website_name)
        else:
            # Standard renewal
            result = subprocess.run(
                ["certbot", "renew", "--cert-name", website.domain],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                cert_path = f"/etc/letsencrypt/live/{website.domain}/fullchain.pem"
                expiry = get_ssl_expiry_date(cert_path)
                
                website.db_set('ssl_expiry_date', expiry)
                frappe.db.commit()
                
                return {'success': True, 'message': 'SSL renewed'}
            else:
                return {'success': False, 'error': result.stderr}
                
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_ssl_expiry_date(cert_path):
    """Get SSL certificate expiry date"""
    try:
        result = subprocess.run(
            ["openssl", "x509", "-enddate", "-noout", "-in", cert_path],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # Parse: notAfter=Dec  1 00:00:00 2025 GMT
            date_str = result.stdout.split('=')[1].strip()
            from datetime import datetime
            expiry = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
            return expiry.strftime('%Y-%m-%d')
        
        return None
    except:
        return None


def update_nginx_ssl_config(domain, cert_file, key_file):
    """Update Nginx config with custom SSL paths"""
    config_file = f"/etc/nginx/sites-available/{domain}"
    
    # Read existing config
    with open(config_file, 'r') as f:
        config = f.read()
    
    # Update SSL paths
    config = config.replace('/etc/letsencrypt/live/', f'/etc/nginx/ssl/')
    
    # Write updated config
    with open(config_file, 'w') as f:
        f.write(config)
    
    # Reload Nginx
    subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
