# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import os
import subprocess
import shlex
import requests
import time
from datetime import datetime, timedelta

@frappe.whitelist()
def get_resource_usage(website_name, period='24h'):
    """Get resource usage statistics for a website"""
    
    # Parse period
    hours = parse_period(period)
    start_time = datetime.now() - timedelta(hours=hours)
    
    # Get usage logs
    logs = frappe.get_all(
        'Resource Usage Log',
        filters={
            'website': website_name,
            'timestamp': ['>=', start_time]
        },
        fields=['timestamp', 'cpu_usage', 'memory_usage', 'disk_usage', 
                'bandwidth_in', 'bandwidth_out', 'request_count', 'error_count'],
        order_by='timestamp asc'
    )
    
    # Calculate averages
    if logs:
        avg_cpu = sum(log.cpu_usage or 0 for log in logs) / len(logs)
        avg_memory = sum(log.memory_usage or 0 for log in logs) / len(logs)
        total_bandwidth = sum((log.bandwidth_in or 0) + (log.bandwidth_out or 0) for log in logs)
        total_requests = sum(log.request_count or 0 for log in logs)
        total_errors = sum(log.error_count or 0 for log in logs)
    else:
        avg_cpu = avg_memory = total_bandwidth = total_requests = total_errors = 0
    
    return {
        'logs': logs,
        'summary': {
            'avg_cpu': round(avg_cpu, 2),
            'avg_memory': round(avg_memory, 2),
            'total_bandwidth': round(total_bandwidth, 2),
            'total_requests': total_requests,
            'total_errors': total_errors,
            'error_rate': round((total_errors / total_requests * 100) if total_requests > 0 else 0, 2)
        }
    }


@frappe.whitelist()
def get_uptime_stats(website_name, period='7d'):
    """Get uptime statistics for a website"""
    
    # Parse period
    hours = parse_period(period)
    start_time = datetime.now() - timedelta(hours=hours)
    
    # Get uptime checks
    checks = frappe.get_all(
        'Uptime Check',
        filters={
            'website': website_name,
            'check_time': ['>=', start_time]
        },
        fields=['check_time', 'is_up', 'status_code', 'response_time', 'error_message'],
        order_by='check_time asc'
    )
    
    # Calculate uptime percentage
    if checks:
        up_count = sum(1 for check in checks if check.is_up)
        uptime_percentage = (up_count / len(checks)) * 100
        avg_response_time = sum(check.response_time or 0 for check in checks if check.is_up) / up_count if up_count > 0 else 0
    else:
        uptime_percentage = 0
        avg_response_time = 0
    
    return {
        'checks': checks,
        'summary': {
            'uptime_percentage': round(uptime_percentage, 2),
            'total_checks': len(checks),
            'successful_checks': sum(1 for check in checks if check.is_up),
            'failed_checks': sum(1 for check in checks if not check.is_up),
            'avg_response_time': round(avg_response_time, 2)
        }
    }


@frappe.whitelist()
def get_bandwidth_usage(website_name, period='30d'):
    """Get bandwidth usage over time"""
    
    hours = parse_period(period)
    start_time = datetime.now() - timedelta(hours=hours)
    
    logs = frappe.get_all(
        'Resource Usage Log',
        filters={
            'website': website_name,
            'timestamp': ['>=', start_time]
        },
        fields=['timestamp', 'bandwidth_in', 'bandwidth_out'],
        order_by='timestamp asc'
    )
    
    total_in = sum(log.bandwidth_in or 0 for log in logs)
    total_out = sum(log.bandwidth_out or 0 for log in logs)
    
    return {
        'logs': logs,
        'total_in': round(total_in, 2),
        'total_out': round(total_out, 2),
        'total': round(total_in + total_out, 2)
    }


@frappe.whitelist()
def check_disk_space(website_name):
    """Check disk space usage for a website"""
    
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        # Get disk usage using du command (Security: Use list)
        cmd = ["du", "-sm", website.site_path]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Parse output (format: "SIZE\tPATH")
            size_mb = int(result.stdout.split('\t')[0])
            return {
                'success': True,
                'disk_usage_mb': size_mb,
                'disk_usage_gb': round(size_mb / 1024, 2)
            }
        else:
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        frappe.log_error(f"Disk space check failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_error_logs(website_name, limit=100):
    """Get recent error logs from Nginx"""
    
    website = frappe.get_doc('Hosted Website', website_name)
    settings = frappe.get_single('Hosting Settings')
    
    # Construct error log path
    error_log = f"/var/log/nginx/{website.domain}_error.log"
    
    try:
        if os.path.exists(error_log):
            cmd = ["tail", "-n", str(limit), error_log]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                return {
                    'success': True,
                    'logs': lines,
                    'count': len(lines)
                }
        
        return {'success': False, 'error': 'Error log not found'}
        
    except Exception as e:
        frappe.log_error(f"Error log retrieval failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def set_alert_threshold(website_name, metric, threshold):
    """Set alert threshold for a metric"""
    
    # Store in website custom fields or separate doctype
    website = frappe.get_doc('Hosted Website', website_name)
    
    # For now, store in notes field (can be enhanced with custom fields)
    thresholds = frappe.parse_json(website.get('alert_thresholds') or '{}')
    thresholds[metric] = threshold
    
    website.db_set('alert_thresholds', frappe.as_json(thresholds))
    
    return {'success': True, 'thresholds': thresholds}


def collect_resource_metrics():
    """Collect resource metrics for all active websites (called by scheduler every 5 minutes)"""
    
    websites = frappe.get_all(
        'Hosted Website',
        filters={'status': 'Active'},
        fields=['name', 'domain', 'site_path']
    )
    
    for website in websites:
        try:
            metrics = get_website_metrics(website)
            
            # Create resource usage log
            frappe.get_doc({
                'doctype': 'Resource Usage Log',
                'website': website.name,
                'timestamp': datetime.now(),
                'cpu_usage': metrics.get('cpu_usage'),
                'memory_usage': metrics.get('memory_usage'),
                'disk_usage': metrics.get('disk_usage'),
                'bandwidth_in': metrics.get('bandwidth_in'),
                'bandwidth_out': metrics.get('bandwidth_out'),
                'request_count': metrics.get('request_count'),
                'error_count': metrics.get('error_count')
            }).insert(ignore_permissions=True)
            
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Resource collection failed for {website.name}: {str(e)}")


def check_uptime():
    """Check uptime for all active websites (called by scheduler every 5 minutes)"""
    
    websites = frappe.get_all(
        'Hosted Website',
        filters={'status': 'Active'},
        fields=['name', 'domain', 'ssl_status']
    )
    
    for website in websites:
        try:
            # Determine protocol
            protocol = 'https' if website.ssl_status == 'Active' else 'http'
            url = f"{protocol}://{website.domain}"
            
            # Make request
            start_time = time.time()
            response = requests.get(url, timeout=10, verify=False)  # nosec B501 — internal health check, certs are self-managed
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Create uptime check
            frappe.get_doc({
                'doctype': 'Uptime Check',
                'website': website.name,
                'check_time': datetime.now(),
                'is_up': response.status_code < 500,
                'status_code': response.status_code,
                'response_time': response_time
            }).insert(ignore_permissions=True)
            
            frappe.db.commit()
            
        except Exception as e:
            # Log failed check
            frappe.get_doc({
                'doctype': 'Uptime Check',
                'website': website.name,
                'check_time': datetime.now(),
                'is_up': 0,
                'error_message': str(e)
            }).insert(ignore_permissions=True)
            
            frappe.db.commit()


def get_website_metrics(website):
    """Get current metrics for a website"""
    
    metrics = {}
    
    try:
        # Get disk usage
        disk_result = check_disk_space(website.name)
        if disk_result.get('success'):
            metrics['disk_usage'] = disk_result.get('disk_usage_mb')
        
        # Get Nginx access log stats for requests
        access_log = f"/var/log/nginx/{website.domain}_access.log"
        if os.path.exists(access_log):
            # Count requests in last 5 minutes (Avoid shell=True by running tail then processing in Python)
            cmd = ["tail", "-n", "1000", access_log]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                metrics['request_count'] = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            else:
                metrics['request_count'] = 0
        
        # Get error count
        error_log = f"/var/log/nginx/{website.domain}_error.log"
        if os.path.exists(error_log):
            cmd = ["tail", "-n", "100", error_log]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                metrics['error_count'] = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            else:
                metrics['error_count'] = 0
        
        # CPU and memory would require more complex monitoring (can use psutil or system commands)
        # For now, set to 0 (can be enhanced)
        metrics['cpu_usage'] = 0
        metrics['memory_usage'] = 0
        metrics['bandwidth_in'] = 0
        metrics['bandwidth_out'] = 0
        
    except Exception as e:
        frappe.log_error(f"Metrics collection failed: {str(e)}")
    
    return metrics


def parse_period(period):
    """Parse period string to hours (e.g., '24h', '7d', '30d')"""
    
    if period.endswith('h'):
        return int(period[:-1])
    elif period.endswith('d'):
        return int(period[:-1]) * 24
    elif period.endswith('w'):
        return int(period[:-1]) * 24 * 7
    else:
        return 24  # Default to 24 hours
