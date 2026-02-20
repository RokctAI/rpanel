# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os
import shutil
import subprocess
import shlex
from datetime import datetime
from rpanel.hosting.mysql_utils import run_mysql_command, run_mysqldump, run_mysql_restore
from rpanel.hosting.service_intelligence import ServiceIntelligence

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
        shutil.copytree(production.site_path, staging_path, dirs_exist_ok=True)
        
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
            subprocess.run([
                "rsync", "-av", "--delete",
                f"{production.site_path}/", f"{staging.staging_path}/"
            ], check=True)
        
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
        subprocess.run([
            "rsync", "-av", "--delete",
            f"{staging.staging_path}/", f"{production.site_path}/"
        ], check=True)
        
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
            shutil.rmtree(staging.staging_path)
        
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
    run_mysql_command(f"CREATE DATABASE IF NOT EXISTS {staging_db}", as_sudo=True)
    
    # Dump production database - Secure: password hidden
    dump_file = f"/tmp/{prod_db}_staging.sql"
    run_mysqldump(
        database=prod_db,
        output_file=dump_file,
        user=db_user,
        password=db_password
    )
    
    # Import to staging database - Secure: password hidden
    run_mysql_restore(
        database=staging_db,
        input_file=dump_file,
        user=db_user,
        password=db_password
    )
    
    # Clean up
    os.remove(dump_file)


def sync_staging_database(source_db, target_db):
    """Sync database from source to target"""
    dump_file = f"/tmp/{source_db}_sync.sql"
    
    # Dump source - Using root without password (assumes auth configured)
    run_mysqldump(
        database=source_db,
        output_file=dump_file,
        user="root",
        as_sudo=True
    )
    
    # Import to target
    run_mysql_restore(
        database=target_db,
        input_file=dump_file,
        user="root",
        as_sudo=True
    )
    
    os.remove(dump_file)


def drop_staging_database(staging_db):
    """Drop staging database"""
    run_mysql_command(f"DROP DATABASE IF EXISTS {staging_db}", as_sudo=True)


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
        fastcgi_pass unix:{ServiceIntelligence.get_php_fpm_socket(php_version)};
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
