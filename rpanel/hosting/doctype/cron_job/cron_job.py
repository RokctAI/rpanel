# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from croniter import croniter
from datetime import datetime
import subprocess
import shlex

class CronJob(Document):
    def validate(self):
        """Validate cron expression and calculate next run"""
        if not self.validate_cron_expression(self.schedule):
            frappe.throw(f"Invalid cron expression: {self.schedule}")
        
        # Calculate next run time
        self.next_run = self.get_next_run_time()
    
    def validate_cron_expression(self, expression):
        """Validate if cron expression is valid"""
        try:
            croniter(expression)
            return True
        except:
            return False
    
    def get_next_run_time(self):
        """Calculate next run time based on cron expression"""
        try:
            cron = croniter(self.schedule, datetime.now())
            return cron.get_next(datetime)
        except Exception as e:
            frappe.log_error(f"Error calculating next run: {str(e)}")
            return None
    
    def execute(self):
        """Execute the cron job"""
        if not self.enabled:
            frappe.throw("Cannot execute disabled cron job")
        
        # Update status
        self.db_set('last_status', 'Running')
        self.db_set('last_run', datetime.now())
        frappe.db.commit()
        
        try:
            # Get website details
            website = frappe.get_doc('Hosted Website', self.website)
            
            # Prepare command
            cmd = self.command
            
            # Execute in website directory
            result = subprocess.run(
                shlex.split(cmd),
                cwd=website.site_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Update status
            if result.returncode == 0:
                self.db_set('last_status', 'Success')
                self.db_set('last_output', result.stdout)
            else:
                self.db_set('last_status', 'Failed')
                self.db_set('last_output', result.stderr)
                
                # Send email notification if enabled
                if self.email_on_failure and self.notification_email:
                    self.send_failure_notification(result.stderr)
            
            # Calculate next run
            self.db_set('next_run', self.get_next_run_time())
            frappe.db.commit()
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout if result.returncode == 0 else result.stderr
            }
            
        except subprocess.TimeoutExpired:
            self.db_set('last_status', 'Failed')
            self.db_set('last_output', 'Command timed out after 5 minutes')
            frappe.db.commit()
            
            if self.email_on_failure and self.notification_email:
                self.send_failure_notification('Command timed out')
            
            return {'success': False, 'output': 'Timeout'}
            
        except Exception as e:
            error_msg = str(e)
            self.db_set('last_status', 'Failed')
            self.db_set('last_output', error_msg)
            frappe.db.commit()
            
            if self.email_on_failure and self.notification_email:
                self.send_failure_notification(error_msg)
            
            frappe.log_error(f"Cron job execution failed: {error_msg}")
            return {'success': False, 'output': error_msg}
    
    def send_failure_notification(self, error_message):
        """Send email notification on job failure"""
        try:
            frappe.sendmail(
                recipients=[self.notification_email],
                subject=f"Cron Job Failed: {self.job_name}",
                message=f"""
                <p>Cron job <strong>{self.job_name}</strong> failed to execute.</p>
                <p><strong>Website:</strong> {self.website}</p>
                <p><strong>Command:</strong> {self.command}</p>
                <p><strong>Error:</strong></p>
                <pre>{error_message}</pre>
                <p><strong>Time:</strong> {datetime.now()}</p>
                """
            )
        except Exception as e:
            frappe.log_error(f"Failed to send cron failure notification: {str(e)}")


@frappe.whitelist()
def execute_cron_job(job_name):
    """Execute a cron job manually"""
    job = frappe.get_doc('Cron Job', job_name)
    return job.execute()


@frappe.whitelist()
def get_cron_templates():
    """Get pre-built cron job templates"""
    return [
        {
            'name': 'Daily Backup',
            'command': 'tar -czf backup-$(date +%Y%m%d).tar.gz .',
            'schedule': '0 2 * * *',
            'description': 'Create daily backup at 2 AM'
        },
        {
            'name': 'Clear Cache',
            'command': 'find ./cache -type f -mtime +7 -delete',
            'schedule': '0 3 * * 0',
            'description': 'Clear cache files older than 7 days, weekly on Sunday at 3 AM'
        },
        {
            'name': 'Update WordPress',
            'command': 'wp core update && wp plugin update --all',
            'schedule': '0 4 * * 1',
            'description': 'Update WordPress core and plugins, weekly on Monday at 4 AM'
        },
        {
            'name': 'Database Optimization',
            'command': 'wp db optimize',
            'schedule': '0 5 * * *',
            'description': 'Optimize WordPress database daily at 5 AM'
        },
        {
            'name': 'Log Rotation',
            'command': 'find ./logs -name "*.log" -mtime +30 -delete',
            'schedule': '0 1 * * *',
            'description': 'Delete log files older than 30 days, daily at 1 AM'
        }
    ]


@frappe.whitelist()
def validate_cron_expression(expression):
    """Validate cron expression and return next 5 run times"""
    try:
        cron = croniter(expression, datetime.now())
        next_runs = []
        for i in range(5):
            next_runs.append(cron.get_next(datetime).strftime('%Y-%m-%d %H:%M:%S'))
        
        return {
            'valid': True,
            'next_runs': next_runs
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }


def execute_scheduled_cron_jobs():
    """Execute all enabled cron jobs that are due (called by scheduler)"""
    now = datetime.now()
    
    # Get all enabled cron jobs where next_run <= now
    jobs = frappe.get_all(
        'Cron Job',
        filters={
            'enabled': 1,
            'next_run': ['<=', now]
        },
        fields=['name']
    )
    
    for job in jobs:
        try:
            job_doc = frappe.get_doc('Cron Job', job.name)
            job_doc.execute()
        except Exception as e:
            frappe.log_error(f"Scheduled cron job execution failed: {str(e)}", f"Cron Job: {job.name}")
