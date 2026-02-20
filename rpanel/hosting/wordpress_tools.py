# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import os
import shutil
import subprocess
import shlex
from rpanel.hosting.mysql_utils import run_mysql_command


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
            shutil.copytree(source_path, website.site_path, dirs_exist_ok=True)

        # Set permissions
        subprocess.run(["chown", "-R", "www-data:www-data", website.site_path], check=True)

        return {'success': True, 'message': 'WordPress imported'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def export_wordpress(website_name, include_uploads=True):
    """Export WordPress site to ZIP"""
    website = frappe.get_doc('Hosted Website', website_name)

    try:
        export_path = f"/tmp/{website.domain}_export.zip"

        cmd = ["zip", "-r", export_path, "."]
        if not include_uploads:
            cmd.extend(["-x", "wp-content/uploads/*"])

        subprocess.run(cmd, cwd=website.site_path, check=True)

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
            # Fallback for PostgreSQL (WP-CLI is MySQL-only)
            if website.db_engine == "PostgreSQL":
                php_script = f"""<?php
define('WP_USE_THEMES', false);
require_once('wp-load.php');

function safe_replace($data, $search, $replace) {{
    if (is_string($data)) {{
        return str_replace($search, $replace, $data);
    }}
    if (is_array($data)) {{
        foreach ($data as &$v) $v = safe_replace($v, $search, $replace);
        return $data;
    }}
    if (is_object($data)) {{
        foreach ($data as $k => &$v) $v = safe_replace($v, $search, $replace);
        return $data;
    }}
    return $data;
}}

function process_table($table, $column, $id_col, $search, $replace) {{
    global $wpdb;
    $rows = $wpdb->get_results("SELECT $id_col, $column FROM $table WHERE $column LIKE '%" . $wpdb->esc_like($search) . "%'");
    foreach ($rows as $row) {{
        $old_val = $row->$column;
        $unserialized = is_serialized($old_val) ? unserialize($old_val) : $old_val;
        $new_val = safe_replace($unserialized, $search, $replace);

        if (is_serialized($old_val)) $new_val = serialize($new_val);

        $wpdb->update($table, array($column => $new_val), array($id_col => $row->$id_col));
    }}
}}

process_table($wpdb->options, 'option_value', 'option_id', '{search}', '{replace}');
process_table($wpdb->posts, 'post_content', 'ID', '{search}', '{replace}');
process_table($wpdb->postmeta, 'meta_value', 'meta_id', '{search}', '{replace}');
echo "Search-replace completed via PHP Bridge\\n";
?>
"""
                script_path = os.path.join(website.site_path, "rpanel_sr.php")
                try:
                    # Write script
                    with open(script_path, "w") as f:
                        f.write(php_script)

                    # Execute as www-data
                    cmd = f"sudo -u www-data php {script_path}"
                    subprocess.run(shlex.split(cmd), check=True, capture_output=True)

                    return {'success': True, 'message': 'Search/replace completed via PG Bridge'}
                finally:
                    if os.path.exists(script_path):
                        os.remove(script_path)

            # Legacy Fallback for MariaDB (Direct SQL for speed, assuming simple strings)
            sql = f"""
            UPDATE wp_options SET option_value = REPLACE(option_value, '{search}', '{replace}');
            UPDATE wp_posts SET post_content = REPLACE(post_content, '{search}', '{replace}');
            UPDATE wp_postmeta SET meta_value = REPLACE(meta_value, '{search}', '{replace}');
            """

            run_mysql_command(
                sql=sql,
                database=website.db_name,
                user=website.db_user,
                password=website.db_password
            )

            return {'success': True, 'message': 'Search/replace completed via Legacy SQL'}
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
