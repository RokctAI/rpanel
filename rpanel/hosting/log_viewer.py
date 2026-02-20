# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import os
import subprocess
import shlex
from datetime import datetime, timedelta

@frappe.whitelist()
def get_nginx_access_log(website_name, lines=100):
    """Get Nginx access log for a website"""
    if website_name == 'local_control_site':
        if "System Manager" not in frappe.get_roles():
            frappe.throw("Access Denied")
        # For local site, maybe return Frappe web logs or global nginx logs if accessible
        # Using frappe.log.web for now as proxy
        log_file = os.path.join(frappe.utils.get_bench_path(), 'logs', 'web.log')
    else:
        website = frappe.get_doc('Hosted Website', website_name)
        log_file = f"/var/log/nginx/{website.domain}_access.log"
    
    return read_log_file(log_file, lines)


@frappe.whitelist()
def get_nginx_error_log(website_name, lines=100):
    """Get Nginx error log for a website"""
    if website_name == 'local_control_site':
        if "System Manager" not in frappe.get_roles():
            frappe.throw("Access Denied")
        # For local site, use frappe.log
        log_file = os.path.join(frappe.utils.get_bench_path(), 'logs', 'frappe.web.log')
    else:
        website = frappe.get_doc('Hosted Website', website_name)
        log_file = f"/var/log/nginx/{website.domain}_error.log"
    
    return read_log_file(log_file, lines)


@frappe.whitelist()
def get_php_error_log(website_name, lines=100):
    """Get PHP error log for a website"""
    if website_name == 'local_control_site':
        if "System Manager" not in frappe.get_roles():
            frappe.throw("Access Denied")
        # Local site is python, return worker logs
        log_file = os.path.join(frappe.utils.get_bench_path(), 'logs', 'worker.log')
    else:
        website = frappe.get_doc('Hosted Website', website_name)
        log_file = os.path.join(website.site_path, 'error.log')
    
    return read_log_file(log_file, lines)


@frappe.whitelist()
def get_application_log(website_name, log_type='debug', lines=100):
    """Get application-specific logs (WordPress, Laravel, etc.)"""
    if website_name == 'local_control_site':
        if "System Manager" not in frappe.get_roles():
            frappe.throw("Access Denied")
        # Local site scheduler logs
        log_file = os.path.join(frappe.utils.get_bench_path(), 'logs', 'schedule.log')
    else:
        website = frappe.get_doc('Hosted Website', website_name)

        # WordPress debug log
        if website.cms_type == 'WordPress':
            log_file = os.path.join(website.site_path, 'wp-content', 'debug.log')
        else:
            # Generic application log
            log_file = os.path.join(website.site_path, 'storage', 'logs', 'laravel.log')
    
    return read_log_file(log_file, lines)


@frappe.whitelist()
def search_logs(website_name, log_type, search_term, lines=500):
    """Search logs for specific term"""
    
    # Get appropriate log file
    if log_type == 'nginx_access':
        result = get_nginx_access_log(website_name, lines)
    elif log_type == 'nginx_error':
        result = get_nginx_error_log(website_name, lines)
    elif log_type == 'php_error':
        result = get_php_error_log(website_name, lines)
    else:
        result = get_application_log(website_name, lines=lines)
    
    if not result.get('success'):
        return result
    
    # Filter lines containing search term
    filtered_lines = [
        line for line in result['lines']
        if search_term.lower() in line.lower()
    ]
    
    return {
        'success': True,
        'lines': filtered_lines,
        'total_matches': len(filtered_lines)
    }


@frappe.whitelist()
def tail_log(website_name, log_type, since_timestamp=None):
    """Get new log entries since timestamp (for live updates)"""
    
    # Get log file path
    if website_name == 'local_control_site':
        if "System Manager" not in frappe.get_roles():
            frappe.throw("Access Denied")

        bench_path = frappe.utils.get_bench_path()
        if log_type == 'nginx_access':
            log_file = os.path.join(bench_path, 'logs', 'web.log')
        elif log_type == 'nginx_error':
            log_file = os.path.join(bench_path, 'logs', 'frappe.web.log')
        elif log_type == 'php_error':
            log_file = os.path.join(bench_path, 'logs', 'worker.log')
        else:
            log_file = os.path.join(bench_path, 'logs', 'schedule.log')
    else:
        website = frappe.get_doc('Hosted Website', website_name)

        if log_type == 'nginx_access':
            log_file = f"/var/log/nginx/{website.domain}_access.log"
        elif log_type == 'nginx_error':
            log_file = f"/var/log/nginx/{website.domain}_error.log"
        elif log_type == 'php_error':
            log_file = os.path.join(website.site_path, 'error.log')
        else:
            log_file = os.path.join(website.site_path, 'wp-content', 'debug.log')
    
    if not os.path.exists(log_file):
        return {'success': False, 'error': 'Log file not found'}
    
    try:
        # Get file modification time
        mod_time = os.path.getmtime(log_file)
        
        # If since_timestamp provided, only return new lines
        if since_timestamp:
            since_dt = datetime.fromisoformat(since_timestamp)
            if datetime.fromtimestamp(mod_time) <= since_dt:
                return {'success': True, 'lines': [], 'has_updates': False}
        
        # Read last 50 lines
        cmd = ["tail", "-n", "50", log_file]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            return {
                'success': True,
                'lines': lines,
                'has_updates': True,
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        frappe.log_error(f"Tail log failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def download_log(website_name, log_type):
    """Download complete log file"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    if log_type == 'nginx_access':
        log_file = f"/var/log/nginx/{website.domain}_access.log"
    elif log_type == 'nginx_error':
        log_file = f"/var/log/nginx/{website.domain}_error.log"
    elif log_type == 'php_error':
        log_file = os.path.join(website.site_path, 'error.log')
    else:
        log_file = os.path.join(website.site_path, 'wp-content', 'debug.log')
    
    if not os.path.exists(log_file):
        frappe.throw("Log file not found")
    
    # Return file path for download
    return {
        'success': True,
        'file_path': log_file,
        'file_name': os.path.basename(log_file)
    }


@frappe.whitelist()
def clear_log(website_name, log_type):
    """Clear log file"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    if log_type == 'nginx_access':
        log_file = f"/var/log/nginx/{website.domain}_access.log"
    elif log_type == 'nginx_error':
        log_file = f"/var/log/nginx/{website.domain}_error.log"
    elif log_type == 'php_error':
        log_file = os.path.join(website.site_path, 'error.log')
    else:
        log_file = os.path.join(website.site_path, 'wp-content', 'debug.log')
    
    if not os.path.exists(log_file):
        return {'success': False, 'error': 'Log file not found'}
    
    try:
        # Truncate log file
        with open(log_file, 'w') as f:
            f.write('')
        
        return {'success': True, 'message': 'Log cleared'}
        
    except Exception as e:
        frappe.log_error(f"Clear log failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_log_stats(website_name):
    """Get statistics about all logs"""
    
    stats = {}
    
    if website_name == 'local_control_site':
        if "System Manager" not in frappe.get_roles():
            frappe.throw("Access Denied")
        bench_path = frappe.utils.get_bench_path()
        logs = {
            'nginx_access': os.path.join(bench_path, 'logs', 'web.log'),
            'nginx_error': os.path.join(bench_path, 'logs', 'frappe.web.log'),
            'php_error': os.path.join(bench_path, 'logs', 'worker.log'),
            'application': os.path.join(bench_path, 'logs', 'schedule.log')
        }
    else:
        website = frappe.get_doc('Hosted Website', website_name)
        logs = {
            'nginx_access': f"/var/log/nginx/{website.domain}_access.log",
            'nginx_error': f"/var/log/nginx/{website.domain}_error.log",
            'php_error': os.path.join(website.site_path, 'error.log'),
            'application': os.path.join(website.site_path, 'wp-content', 'debug.log')
        }
    
    for log_type, log_file in logs.items():
        if os.path.exists(log_file):
            try:
                # Get file size
                size_bytes = os.path.getsize(log_file)
                size_mb = round(size_bytes / (1024 * 1024), 2)
                
                # Get line count (Avoid shell=True)
                cmd = ["wc", "-l", log_file]
                result = subprocess.run(cmd, capture_output=True, text=True)
                line_count = int(result.stdout.split()[0]) if result.returncode == 0 else 0
                
                # Get last modified time
                mod_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                
                stats[log_type] = {
                    'exists': True,
                    'size_mb': size_mb,
                    'line_count': line_count,
                    'last_modified': mod_time.strftime('%Y-%m-%d %H:%M:%S')
                }
            except Exception as e:
                stats[log_type] = {'exists': True, 'error': str(e)}
        else:
            stats[log_type] = {'exists': False}
    
    return {'success': True, 'stats': stats}


def read_log_file(log_file, lines=100):
    """Helper function to read log file"""
    if not os.path.exists(log_file):
        return {'success': False, 'error': 'Log file not found'}
    
    try:
        # Use tail to get last N lines (Avoid shell=True)
        cmd = ["tail", "-n", str(lines), log_file]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            lines_list = result.stdout.strip().split('\n') if result.stdout.strip() else []
            return {
                'success': True,
                'lines': lines_list,
                'total_lines': len(lines_list)
            }
        else:
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        frappe.log_error(f"Read log file failed: {str(e)}")
        return {'success': False, 'error': str(e)}
