# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os
import subprocess
import shlex
from datetime import datetime

class StagingEnvironment(Document):
    pass


@frappe.whitelist()
def create_staging(production_website_name):
    """Create staging environment for production website"""
    production = frappe.get_doc('Hosted Website', production_website_name)
    
    # Generate staging name
    staging_name = f"{production.domain}_staging"
    staging_url = f"staging.{production.domain}"
    staging_path = f"/var/www/staging_{production.domain.replace('.', '_')}"
    staging_db = f"staging_{production.db_name}"
    
    try:
        # Create staging directory
        os.makedirs(staging_path, exist_ok=True)
        
        # Copy production files to staging
        cmd = f"cp -r {production.site_path}/* {staging_path}/"
        subprocess.run(cmd, shell=True, check=True)
        
        # Create staging database
        create_staging_database(production.db_name, staging_db, production.db_user, production.db_password)
        
        # Create Nginx config for staging
        create_staging_nginx_config(staging_url, staging_path, production.php_version)
        
        # Create staging environment record
        staging = frappe.get_doc({
            'doctype': 'Staging Environment',
            'staging_name': staging_name,
            'production_website': production_website_name,
            'staging_url': staging_url,
            'staging_path': staging_path,
            'staging_database': staging_db,
            'status': 'Active',
            'last_sync': datetime.now()
        })
        staging.insert()
        frappe.db.commit()
        
        return {
            'success': True,
            'staging_name': staging_name,
            'staging_url': staging_url
        }
        
    except Exception as e:
        frappe.log_error(f"Create staging failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def sync_to_staging(staging_name, sync_database=True, sync_files=True):
    """Sync production to staging"""
    staging = frappe.get_doc('Staging Environment', staging_name)
    production = frappe.get_doc('Hosted Website', staging.production_website)
    
    try:
        staging.db_set('status', 'Syncing')
        frappe.db.commit()
        
        # Sync files
        if sync_files:
            cmd = f"rsync -av --delete {production.site_path}/ {staging.staging_path}/"
            subprocess.run(cmd, shell=True, check=True)
        
        # Sync database
        if sync_database:
            sync_staging_database(production.db_name, staging.staging_database)
        
        staging.db_set('status', 'Active')
        staging.db_set('last_sync', datetime.now())
        frappe.db.commit()
        
        return {'success': True, 'message': 'Staging synced'}
        
    except Exception as e:
        staging.db_set('status', 'Active')
        frappe.db.commit()
        frappe.log_error(f"Sync to staging failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def push_to_production(staging_name):
    """Push staging changes to production"""
    staging = frappe.get_doc('Staging Environment', staging_name)
    production = frappe.get_doc('Hosted Website', staging.production_website)
    
    try:
        # Create backup of production first
        frappe.call('rpanel.hosting.doctype.site_backup.site_backup.create_backup',
                   website_name=production.name, backup_type='Full')
        
        # Sync files from staging to production
        cmd = f"rsync -av --delete {staging.staging_path}/ {production.site_path}/"
        subprocess.run(cmd, shell=True, check=True)
        
        # Sync database from staging to production
        sync_staging_database(staging.staging_database, production.db_name)
        
        return {'success': True, 'message': 'Pushed to production'}
        
    except Exception as e:
        frappe.log_error(f"Push to production failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def delete_staging(staging_name):
    """Delete staging environment"""
    staging = frappe.get_doc('Staging Environment', staging_name)
    
    try:
        # Remove staging directory
        if os.path.exists(staging.staging_path):
            cmd = f"rm -rf {staging.staging_path}"
            subprocess.run(cmd, shell=True, check=True)
        
        # Drop staging database
        drop_staging_database(staging.staging_database)
        
        # Remove Nginx config
        remove_staging_nginx_config(staging.staging_url)
        
        # Delete staging record
        staging.delete()
        frappe.db.commit()
        
        return {'success': True, 'message': 'Staging deleted'}
        
    except Exception as e:
        frappe.log_error(f"Delete staging failed: {str(e)}")
        return {'success': False, 'error': str(e)}


def create_staging_database(prod_db, staging_db, db_user, db_password):
    """Create staging database from production"""
    # Create database
    cmd = f"mysql -u root -e 'CREATE DATABASE IF NOT EXISTS {staging_db}'"
    subprocess.run(cmd, shell=True, check=True)
    
    # Dump production database
    dump_file = f"/tmp/{prod_db}_staging.sql"
    cmd = f"mysqldump -u {db_user} -p{db_password} {prod_db} > {dump_file}"
    subprocess.run(cmd, shell=True, check=True)
    
    # Import to staging database
    cmd = f"mysql -u {db_user} -p{db_password} {staging_db} < {dump_file}"
    subprocess.run(cmd, shell=True, check=True)
    
    # Clean up
    os.remove(dump_file)


def sync_staging_database(source_db, target_db):
    """Sync database from source to target"""
    dump_file = f"/tmp/{source_db}_sync.sql"
    
    # Dump source
    cmd = f"mysqldump -u root {source_db} > {dump_file}"
    subprocess.run(cmd, shell=True, check=True)
    
    # Import to target
    cmd = f"mysql -u root {target_db} < {dump_file}"
    subprocess.run(cmd, shell=True, check=True)
    
    os.remove(dump_file)


def drop_staging_database(staging_db):
    """Drop staging database"""
    cmd = f"mysql -u root -e 'DROP DATABASE IF EXISTS {staging_db}'"
    subprocess.run(cmd, shell=True, check=True)


def create_staging_nginx_config(staging_url, staging_path, php_version):
    """Create Nginx config for staging"""
    config = f"""
server {{
    listen 80;
    server_name {staging_url};
    root {staging_path};
    index index.php index.html;
    
    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}
    
    location ~ \\.php$ {{
        fastcgi_pass unix:/run/php/php{php_version}-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }}
}}
"""
    
    config_file = f"/etc/nginx/sites-available/{staging_url}"
    with open(config_file, 'w') as f:
        f.write(config)
    
    # Enable site
    link = f"/etc/nginx/sites-enabled/{staging_url}"
    if not os.path.exists(link):
        os.symlink(config_file, link)
    
    # Reload Nginx
    subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], check=True)


def remove_staging_nginx_config(staging_url):
    """Remove Nginx config for staging"""
    config_file = f"/etc/nginx/sites-available/{staging_url}"
    link = f"/etc/nginx/sites-enabled/{staging_url}"
    
    if os.path.exists(link):
        os.remove(link)
    if os.path.exists(config_file):
        os.remove(config_file)
    
    subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], check=True)
