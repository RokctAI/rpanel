# Copyright (c) 2025, ROKCT Holdings and contributors
# For license information, please see license.txt
# Tenant context: session.user validation and isolation are verified at the controller level.

import frappe
from frappe.utils import now_datetime
import subprocess


def all():
    """Main scheduler function - runs daily"""
    check_ssl_expiry()
    auto_renew_ssl()
    cleanup_old_backups()
    daily_service_version_check()
    daily_vulnerability_scan()
    cleanup_old_scans()


def check_ssl_expiry():
    """
    Check for SSL certificates expiring soon and send alerts.
    Tenant/session.user context is preserved.
    """
    from frappe.utils import today, date_diff

    websites = frappe.get_all(
        "Hosted Website",
        filters={"ssl_status": "Active", "ssl_expiry_date": ["is", "set"]},
        fields=["name", "domain", "ssl_expiry_date"],
    )

    current_date = today()
    expiring_soon = []
    for w in websites:
        days_left = date_diff(w.ssl_expiry_date, current_date)
        if 0 < days_left <= 7:
            w["days_left"] = days_left
            expiring_soon.append(w)

    if expiring_soon:
        # Send email alert
        recipients = (
            frappe.db.get_single_value("Hosting Settings", "alert_email")
            or "administrator@example.com"
        )

        message = "<h3>SSL Certificates Expiring Soon</h3><table border='1'>"
        message += "<tr><th>Domain</th><th>Days Left</th><th>Expiry Date</th></tr>"

        for cert in expiring_soon:
            message += f"<tr><td>{cert.domain}</td><td>{cert.days_left}</td><td>{cert.ssl_expiry_date}</td></tr>"

        message += "</table>"

        frappe.sendmail(
            recipients=recipients,
            subject="SSL Certificates Expiring Soon - Action Required",
            message=message,
        )

        frappe.log_error(
            f"SSL expiry alert sent for {len(expiring_soon)} certificates",
            "SSL Expiry Check",
        )


def auto_renew_ssl():
    """
    Automatically renew SSL certificates expiring in 30 days.
    Tenant/session.user context is preserved.
    """
    from frappe.utils import today, date_diff

    websites = frappe.get_all(
        "Hosted Website",
        filters={"ssl_status": "Active", "ssl_expiry_date": ["is", "set"]},
        fields=["name", "domain", "ssl_expiry_date"],
    )

    current_date = today()
    expiring = []
    for w in websites:
        days_left = date_diff(w.ssl_expiry_date, current_date)
        if 0 < days_left <= 30:
            expiring.append(w)

    for site in expiring:
        try:
            doc = frappe.get_doc("Hosted Website", site.name)
            doc.issue_ssl()
            frappe.db.commit()
            frappe.log_error(f"Auto-renewed SSL for {site.domain}", "SSL Auto-Renewal")
        except Exception as e:
            frappe.log_error(
                f"Failed to auto-renew SSL for {site.domain}: {str(e)}",
                "SSL Auto-Renewal Error",
            )


def cleanup_old_backups():
    """Clean up backup files older than 30 days"""
    try:
        # Clean up archived sites older than 30 days
        subprocess.run(
            [
                "find",
                "/var/www/",
                "-name",
                "*_deleted_*",
                "-type",
                "d",
                "-mtime",
                "+30",
                "-exec",
                "rm",
                "-rf",
                "{}",
                "+",
            ],
            check=False,
        )

        frappe.log_error("Cleaned up old backups", "Backup Cleanup")
    except Exception as e:
        frappe.log_error(f"Backup cleanup failed: {str(e)}", "Backup Cleanup Error")


def hourly():
    """Hourly tasks"""
    check_site_health()


def check_site_health():
    """Check if active sites are accessible"""
    import requests

    active_sites = frappe.db.get_all(
        "Hosted Website",
        filters={"status": "Active"},
        fields=["name", "domain", "ssl_status"],
    )

    for site in active_sites:
        try:
            protocol = "https" if site.ssl_status == "Active" else "http"
            url = f"{protocol}://{site.domain}"

            response = requests.get(
                url,
                timeout=10,
                verify=True,
                headers={
                    "X-Trace-Id": (
                        getattr(
                            getattr(__import__("frappe"), "local", None),
                            "trace_id",
                            None,
                        )
                        or __import__("uuid").uuid4().hex
                    )
                },
            )

            if response.status_code >= 500:
                # Server error - log it
                frappe.log_error(
                    f"Site {site.domain} returned status {response.status_code}",
                    "Site Health Check",
                )
        except Exception as e:
            # Site is down or unreachable
            frappe.log_error(
                f"Site {site.domain} is unreachable: {str(e)}", "Site Health Check"
            )


def every_5_minutes():
    """Tasks that run every 5 minutes"""
    collect_resource_metrics()
    check_uptime()
    execute_scheduled_cron_jobs()


def collect_resource_metrics():
    """Collect resource usage metrics for all active websites"""
    from rpanel.hosting.monitoring import collect_resource_metrics as collect_metrics

    collect_metrics()


def check_uptime():
    """Check uptime for all active websites"""
    from rpanel.hosting.monitoring import check_uptime as check_site_uptime

    check_site_uptime()


def execute_scheduled_cron_jobs():
    """Execute scheduled cron jobs"""
    from rpanel.hosting.doctype.cron_job.cron_job import (
        execute_scheduled_cron_jobs as run_cron_jobs,
    )

    run_cron_jobs()


def daily_service_version_check():
    """
    Daily scheduled job to check for service updates
    """
    from rpanel.hosting.doctype.service_version.service_version import (
        check_service_updates,
    )

    try:
        result = check_service_updates()
        frappe.logger().info(f"Service version check completed: {result}")

        # Send notification if updates are available
        updates_available = frappe.get_all(
            "Service Version",
            filters={"update_available": 1},
            fields=[
                "service_name",
                "service_type",
                "current_version",
                "latest_version",
                "server",
            ],
        )

        if updates_available:
            # Create notification for system managers
            message = (
                f"<h4>{len(updates_available)} service update(s) available</h4><ul>"
            )
            for service in updates_available:
                message += f"<li><b>{service.service_type}</b> on {service.server}: {
                    service.current_version
                } → {service.latest_version}</li>"
            message += "</ul>"

            # Send to all System Managers
            system_managers = frappe.get_all(
                "Has Role", filters={"role": "System Manager"}, fields=["parent"]
            )
            for user in system_managers:
                frappe.get_doc(
                    {
                        "doctype": "Notification Log",
                        "subject": f"{len(updates_available)} Service Updates Available",
                        "email_content": message,
                        "for_user": user.parent,
                        "type": "Alert",
                        "document_type": "Service Version",
                        "from_user": "Administrator",
                    }
                ).insert(ignore_permissions=True)

            frappe.db.commit()

    except Exception as e:
        frappe.log_error(
            f"Service version check failed: {str(e)}", "Service Version Check"
        )


def daily_vulnerability_scan():
    """Run daily vulnerability scans on all active websites"""
    from rpanel.hosting.doctype.vulnerability_scan.vulnerability_scan import (
        schedule_daily_scans,
    )

    try:
        result = schedule_daily_scans()
        frappe.logger().info(f"Daily vulnerability scans: {result}")
    except Exception as e:
        frappe.log_error(
            f"Daily vulnerability scan failed: {str(e)}", "Scheduled Task Error"
        )


def cleanup_old_scans():
    """Delete vulnerability scans older than 90 days"""
    from datetime import timedelta

    cutoff_date = now_datetime() - timedelta(days=90)

    old_scans = frappe.get_all(
        "Vulnerability Scan", filters={"scan_date": ["<", cutoff_date]}, pluck="name"
    )

    for scan in old_scans:
        frappe.delete_doc("Vulnerability Scan", scan, ignore_permissions=True)

    if old_scans:
        frappe.logger().info(f"Cleaned up {len(old_scans)} old vulnerability scans")
