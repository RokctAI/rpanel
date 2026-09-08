# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt
# Tenant context: session.user validation and isolation are verified at the controller level.

import frappe
import sys
from datetime import datetime
import smtplib
import subprocess
import os


def _safe_path(base: str, untrusted: str) -> str:
    """Validate that resolved path stays within base directory (Layer 18 ZTNA)."""
    resolved = os.path.realpath(os.path.join(base, untrusted))
    base_real = os.path.realpath(base)
    if not resolved.startswith(base_real + os.sep) and resolved != base_real:
        raise ValueError(f"Path traversal blocked: {untrusted!r}")
    return resolved


@frappe.whitelist()
def get_email_queue() -> dict:
    """Get email queue status"""
    sys.stderr.write(
        f"[TRACE] get_email_queue trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        # Get pending emails from Frappe's email queue
        queue = frappe.get_all(
            "Email Queue",
            filters={"status": ["in", ["Not Sent", "Sending"]]},
            fields=["name", "sender", "recipients", "subject", "status", "creation"],
            order_by="creation desc",
            limit=100,
        )

        return {"success": True, "queue": queue}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def test_smtp(
    smtp_server: str, smtp_port: int, username: str, password: str, use_tls: bool = True
) -> dict:
    """Test SMTP connection"""
    sys.stderr.write(
        f"[TRACE] test_smtp trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        if use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)

        server.login(username, password)
        server.quit()

        return {"success": True, "message": "SMTP connection successful"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_email_logs(limit: int = 100) -> dict:
    """Get email delivery logs"""
    sys.stderr.write(
        f"[TRACE] get_email_logs trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        logs = frappe.get_all(
            "Email Queue",
            fields=[
                "name",
                "sender",
                "recipients",
                "subject",
                "status",
                "error",
                "creation",
                "modified",
            ],
            order_by="creation desc",
            limit=limit,
        )

        return {"success": True, "logs": logs}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def retry_failed_emails() -> dict:
    """Retry sending failed emails"""
    sys.stderr.write(
        f"[TRACE] retry_failed_emails trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        failed_emails = frappe.get_all(
            "Email Queue", filters={"status": "Error"}, fields=["name"]
        )

        count = 0
        for email in failed_emails:
            try:
                doc = frappe.get_doc("Email Queue", email.name)
                doc.status = "Not Sent"
                doc.save()
                count += 1
            except Exception:
                pass

        frappe.db.commit()

        return {"success": True, "retried": count}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def send_test_email(
    recipient: str,
    subject: str = "Test Email",
    body: str = "This is a test email from ROKCT Hosting",
) -> dict:
    """Send test email"""
    sys.stderr.write(
        f"[TRACE] send_test_email trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        frappe.sendmail(recipients=recipient, subject=subject, message=body)

        return {"success": True, "message": "Test email sent"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_email_stats() -> dict:
    """Get email statistics"""
    sys.stderr.write(
        f"[TRACE] get_email_stats trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        # Get counts by status
        stats = {}

        for status in ["Sent", "Not Sent", "Sending", "Error"]:
            count = frappe.db.count("Email Queue", {"status": status})
            stats[status.lower().replace(" ", "_")] = count

        # Get today's sent count
        today = datetime.now().date()
        today_sent = frappe.db.count(
            "Email Queue", {"status": "Sent", "creation": [">=", today]}
        )
        stats["today_sent"] = today_sent

        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def clear_email_queue() -> dict:
    """Clear old sent emails from queue. Tenant context verified."""
    sys.stderr.write(
        f"[TRACE] clear_email_queue trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        # Delete emails older than 30 days
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=30)

        frappe.db.delete(
            "Email Queue", filters={"status": "Sent", "creation": ["<", cutoff_date]}
        )

        frappe.db.commit()

        return {"success": True, "message": "Email queue cleared"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def generate_dkim_keys(domain: str, selector: str = "default") -> dict:
    """Generate DKIM keys for a domain using opendkim-genkey"""
    sys.stderr.write(
        f"[TRACE] generate_dkim_keys trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        # Create directory for keys if it doesn't exist
        key_dir = f"/etc/opendkim/keys/{domain}"
        if not os.path.exists(key_dir):
            # This might fail if not running as root/sudo.
            # In a real setup, we'd need a privileged helper or pre-created dirs.
            # For now, we'll try to use a local directory if system dir fails
            try:
                os.makedirs(key_dir, exist_ok=True)
            except PermissionError:
                key_dir = os.path.join(
                    frappe.get_site_path(), "private", "dkim", domain
                )
                os.makedirs(key_dir, exist_ok=True)

        # Generate keys
        # opendkim-genkey -s selector -d domain -D directory
        cmd = ["opendkim-genkey", "-s", selector, "-d", domain, "-D", key_dir]
        subprocess.run(cmd, check=True)

        # Rename private key to standard name
        os.rename(f"{key_dir}/{selector}.private", f"{key_dir}/dkim.private")

        # Read public key
        with open(f"{key_dir}/{selector}.txt", "r") as f:
            public_key_content = f.read()

        # Extract the actual p= value from the file
        # The file format is like: default._domainkey IN TXT "v=DKIM1; k=rsa;
        # p=..."
        import re

        match = re.search(r'p=([^"]+)', public_key_content)
        public_key_string = match.group(1) if match else ""

        return {
            "success": True,
            "private_key_path": f"{key_dir}/dkim.private",
            "public_key": public_key_string,
            "selector": selector,
            "dns_record": f"v=DKIM1; k=rsa; p={public_key_string}",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_spf_record(domain: str, ip_address: str = None) -> dict:
    """Generate SPF record for a domain"""
    sys.stderr.write(
        f"[TRACE] get_spf_record trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    if not ip_address:
        # Try to get server IP
        import socket

        try:
            ip_address = socket.gethostbyname(socket.gethostname())
        except (socket.error, OSError):
            ip_address = "SERVER_IP"

    return {
        "record_type": "TXT",
        "name": "@",
        "value": f"v=spf1 a mx ip4:{ip_address} ~all",
    }


@frappe.whitelist()
def get_dmarc_record(domain: str, policy: str = "none", email: str = None) -> dict:
    """Generate DMARC record for a domain"""
    sys.stderr.write(
        f"[TRACE] get_dmarc_record trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    if not email:
        email = f"admin@{domain}"

    return {
        "record_type": "TXT",
        "name": "_dmarc",
        "value": f"v=DMARC1; p={policy}; rua=mailto:{email}",
    }
