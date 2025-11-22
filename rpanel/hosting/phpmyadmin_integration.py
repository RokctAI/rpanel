# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import subprocess
import os

@frappe.whitelist()
def setup_phpmyadmin(website_name):
    """Setup phpMyAdmin for a website"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        # Download phpMyAdmin if not exists
        phpmyadmin_path = "/usr/share/phpmyadmin"
        if not os.path.exists(phpmyadmin_path):
            # Download latest phpMyAdmin
            cmd = "cd /tmp && wget https://www.phpmyadmin.net/downloads/phpMyAdmin-latest-all-languages.tar.gz"
            subprocess.run(cmd, shell=True, check=True)
            
            # Extract
            cmd = "cd /tmp && tar -xzf phpMyAdmin-latest-all-languages.tar.gz"
            subprocess.run(cmd, shell=True, check=True)
            
            # Move to /usr/share
            cmd = "mv /tmp/phpMyAdmin-*-all-languages /usr/share/phpmyadmin"
            subprocess.run(cmd, shell=True, check=True)
        
        # Create symlink in website directory
        pma_link = os.path.join(website.site_path, 'phpmyadmin')
        if not os.path.exists(pma_link):
            os.symlink(phpmyadmin_path, pma_link)
        
        # Create config file
        config_file = os.path.join(pma_link, 'config.inc.php')
        config = f"""<?php
$cfg['blowfish_secret'] = '{frappe.generate_hash(length=32)}';
$i = 0;
$i++;
$cfg['Servers'][$i]['auth_type'] = 'cookie';
$cfg['Servers'][$i]['host'] = 'localhost';
$cfg['Servers'][$i]['compress'] = false;
$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['UploadDir'] = '';
$cfg['SaveDir'] = '';
?>
"""
        with open(config_file, 'w') as f:
            f.write(config)
        
        # Set permissions
        subprocess.run(f"chown -R www-data:www-data {pma_link}", shell=True, check=True)
        
        pma_url = f"https://{website.domain}/phpmyadmin"
        
        return {
            'success': True,
            'url': pma_url,
            'message': 'phpMyAdmin installed'
        }
        
    except Exception as e:
        frappe.log_error(f"phpMyAdmin setup failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_phpmyadmin_url(website_name):
    """Get phpMyAdmin URL for website"""
    website = frappe.get_doc('Hosted Website', website_name)
    pma_link = os.path.join(website.site_path, 'phpmyadmin')
    
    if os.path.exists(pma_link):
        return {
            'success': True,
            'url': f"https://{website.domain}/phpmyadmin"
        }
    else:
        return {'success': False, 'error': 'phpMyAdmin not installed'}
