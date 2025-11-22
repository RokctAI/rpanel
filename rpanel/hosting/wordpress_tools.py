# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import os
import subprocess
import shlex

@frappe.whitelist()
def import_wordpress(website_name, source_path):
    """Import WordPress site from ZIP or directory"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        # Extract if ZIP
        if source_path.endswith('.zip'):
            cmd = f"unzip -o {source_path} -d {website.site_path}"
            subprocess.run(shlex.split(cmd), check=True)
        else:
            # Copy directory
            cmd = f"cp -r {source_path}/* {website.site_path}/"
            subprocess.run(cmd, shell=True, check=True)
        
        # Set permissions
        subprocess.run(f"chown -R www-data:www-data {website.site_path}", shell=True, check=True)
        
        return {'success': True, 'message': 'WordPress imported'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def export_wordpress(website_name, include_uploads=True):
    """Export WordPress site to ZIP"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        export_path = f"/tmp/{website.domain}_export.zip"
        
        if include_uploads:
            cmd = f"cd {website.site_path} && zip -r {export_path} ."
        else:
            cmd = f"cd {website.site_path} && zip -r {export_path} . -x 'wp-content/uploads/*'"
        
        subprocess.run(cmd, shell=True, check=True)
        
        return {'success': True, 'file_path': export_path}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def search_replace_db(website_name, search, replace):
    """Search and replace in WordPress database"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        # Use WP-CLI if available
        cmd = f"wp search-replace '{search}' '{replace}' --path={website.site_path}"
        result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
        
        if result.returncode == 0:
            return {'success': True, 'output': result.stdout}
        else:
            # Fallback to manual SQL
            sql = f"""
            UPDATE wp_options SET option_value = REPLACE(option_value, '{search}', '{replace}');
            UPDATE wp_posts SET post_content = REPLACE(post_content, '{search}', '{replace}');
            UPDATE wp_postmeta SET meta_value = REPLACE(meta_value, '{search}', '{replace}');
            """
            
            cmd = f"mysql -u {website.db_user} -p{website.db_password} {website.db_name} -e \"{sql}\""
            subprocess.run(cmd, shell=True, check=True)
            
            return {'success': True, 'message': 'Search/replace completed'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def install_wp_plugin(website_name, plugin_slug):
    """Install WordPress plugin"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        cmd = f"wp plugin install {plugin_slug} --activate --path={website.site_path}"
        result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
        
        return {'success': True, 'output': result.stdout}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def update_wordpress(website_name):
    """Update WordPress core"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        cmd = f"wp core update --path={website.site_path}"
        result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
        
        return {'success': True, 'output': result.stdout}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_wp_info(website_name):
    """Get WordPress installation info"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        # Get WP version
        cmd = f"wp core version --path={website.site_path}"
        version_result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
        
        # Get plugin list
        cmd = f"wp plugin list --format=json --path={website.site_path}"
        plugins_result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
        
        import json
        plugins = json.loads(plugins_result.stdout) if plugins_result.returncode == 0 else []
        
        return {
            'success': True,
            'version': version_result.stdout.strip(),
            'plugins': plugins
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
