# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@frappe.whitelist()
def get_email_queue():
    """Get email queue status"""
    try:
        # Get pending emails from Frappe's email queue
        queue = frappe.get_all(
            'Email Queue',
            filters={'status': ['in', ['Not Sent', 'Sending']]},
            fields=['name', 'sender', 'recipients', 'subject', 'status', 'creation'],
            order_by='creation desc',
            limit=100
        )
        
        return {'success': True, 'queue': queue}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def test_smtp(smtp_server, smtp_port, username, password, use_tls=True):
    """Test SMTP connection"""
    try:
        if use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        
        server.login(username, password)
        server.quit()
        
        return {'success': True, 'message': 'SMTP connection successful'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_email_logs(limit=100):
    """Get email delivery logs"""
    try:
        logs = frappe.get_all(
            'Email Queue',
            fields=['name', 'sender', 'recipients', 'subject', 'status', 'error', 'creation', 'modified'],
            order_by='creation desc',
            limit=limit
        )
        
        return {'success': True, 'logs': logs}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def retry_failed_emails():
    """Retry sending failed emails"""
    try:
        failed_emails = frappe.get_all(
            'Email Queue',
            filters={'status': 'Error'},
            fields=['name']
        )
        
        count = 0
        for email in failed_emails:
            try:
                doc = frappe.get_doc('Email Queue', email.name)
                doc.status = 'Not Sent'
                doc.save()
                count += 1
            except:
                pass
        
        frappe.db.commit()
        
        return {'success': True, 'retried': count}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def send_test_email(recipient, subject='Test Email', body='This is a test email from ROKCT Hosting'):
    """Send test email"""
    try:
        frappe.sendmail(
            recipients=recipient,
            subject=subject,
            message=body
        )
        
        return {'success': True, 'message': 'Test email sent'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_email_stats():
    """Get email statistics"""
    try:
        # Get counts by status
        stats = {}
        
        for status in ['Sent', 'Not Sent', 'Sending', 'Error']:
            count = frappe.db.count('Email Queue', {'status': status})
            stats[status.lower().replace(' ', '_')] = count
        
        # Get today's sent count
        today = datetime.now().date()
        today_sent = frappe.db.count('Email Queue', {
            'status': 'Sent',
            'creation': ['>=', today]
        })
        stats['today_sent'] = today_sent
        
        return {'success': True, 'stats': stats}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def clear_email_queue():
    """Clear old sent emails from queue"""
    try:
        # Delete emails older than 30 days
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=30)
        
        frappe.db.sql("""
            DELETE FROM `tabEmail Queue`
            WHERE status = 'Sent'
            AND creation < %s
        """, (cutoff_date,))
        
        frappe.db.commit()
        
        return {'success': True, 'message': 'Email queue cleared'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
