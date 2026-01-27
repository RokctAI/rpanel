# Copyright (c) 2025, Rokct Intelligence (pty) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os
import subprocess
import shlex
from datetime import datetime
import boto3
from google.cloud import storage as gcs_storage
import dropbox
from rpanel.hosting.mysql_utils import run_mysqldump, run_mysql_restore

class SiteBackup(Document):
    def before_save(self):
        """Set default backup date if not set"""
        if not self.backup_date:
            self.backup_date = datetime.now()
    
    def create_backup(self):
        """Create backup based on backup type"""
        try:
            self.db_set('status', 'In Progress')
            frappe.db.commit()
            
            # Get website details
            website = frappe.get_doc('Hosted Website', self.website)
            
            # Get hosting settings for backup directory
            settings = frappe.get_single('Hosting Settings')
            backup_dir = settings.get('backup_directory') or '/var/backups/websites'
            
            # Ensure backup directory exists
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{website.domain}_{timestamp}"
            
            if self.backup_type == 'Full':
                backup_file = self.create_full_backup(website, backup_dir, backup_name)
            elif self.backup_type == 'Database Only':
                backup_file = self.create_database_backup(website, backup_dir, backup_name)
            elif self.backup_type == 'Files Only':
                backup_file = self.create_files_backup(website, backup_dir, backup_name)
            
            # Get file size
            file_size = os.path.getsize(backup_file)
            
            # Check if encryption is enabled
            security_settings = frappe.get_single('Security Settings')
            is_encrypted = 0
            
            if security_settings.enable_backup_encryption:
                try:
                    from rpanel.hosting.backup_encryption import encrypt_backup
                    
                    # Encrypt the file
                    encrypted_file = encrypt_backup(backup_file)
                    
                    # Remove original unencrypted file
                    os.remove(backup_file)
                    
                    # Update path and size
                    backup_file = encrypted_file
                    file_size = os.path.getsize(backup_file)
                    is_encrypted = 1
                    
                except Exception as e:
                    frappe.log_error(f"Backup encryption failed: {str(e)}", "Backup Encryption Error")
                    # Continue with unencrypted backup, but log error
            
            # Update backup record
            self.db_set('file_path', backup_file)
            self.db_set('file_size', file_size)
            self.db_set('is_encrypted', is_encrypted)
            self.db_set('status', 'Completed')
            frappe.db.commit()
            
            # Upload to cloud if configured
            if self.cloud_storage != 'None':
                self.upload_to_cloud(backup_file)
            
            return {'success': True, 'file_path': backup_file, 'file_size': file_size}
            
        except Exception as e:
            self.db_set('status', 'Failed')
            self.db_set('notes', str(e))
            frappe.db.commit()
            frappe.log_error(f"Backup creation failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_full_backup(self, website, backup_dir, backup_name):
        """Create full backup (files + database)"""
        backup_file = os.path.join(backup_dir, f"{backup_name}_full.tar.gz")
        
        # Create database dump first
        db_dump = self.dump_database(website, backup_dir, backup_name)
        
        # Create tarball with files and database
        cmd = f"tar -czf {backup_file} -C {website.site_path} . -C {backup_dir} {os.path.basename(db_dump)}"
        subprocess.run(shlex.split(cmd), check=True)
        
        # Remove temporary database dump
        os.remove(db_dump)
        
        return backup_file
    
    def create_database_backup(self, website, backup_dir, backup_name):
        """Create database-only backup"""
        return self.dump_database(website, backup_dir, backup_name)
    
    def create_files_backup(self, website, backup_dir, backup_name):
        """Create files-only backup"""
        backup_file = os.path.join(backup_dir, f"{backup_name}_files.tar.gz")
        cmd = f"tar -czf {backup_file} -C {website.site_path} ."
        subprocess.run(shlex.split(cmd), check=True)
        return backup_file
    
    def dump_database(self, website, backup_dir, backup_name):
        """Dump database to SQL file"""
        db_file = os.path.join(backup_dir, f"{backup_name}_db.sql")
        # Secure: Password hidden from process list via temp config file
        run_mysqldump(
            database=website.db_name,
            output_file=db_file,
            user=website.db_user,
            password=website.db_password
        )
        return db_file
    
    def upload_to_cloud(self, backup_file):
        """Upload backup to configured cloud storage"""
        try:
            if self.cloud_storage == 'AWS S3':
                url = self.upload_to_s3(backup_file)
            elif self.cloud_storage == 'Google Cloud Storage':
                url = self.upload_to_gcs(backup_file)
            elif self.cloud_storage == 'Dropbox':
                url = self.upload_to_dropbox(backup_file)
            else:
                return
            
            self.db_set('cloud_url', url)
            frappe.db.commit()
            
        except Exception as e:
            frappe.log_error(f"Cloud upload failed: {str(e)}")
    
    def upload_to_s3(self, backup_file):
        """Upload to AWS S3"""
        settings = frappe.get_single('Hosting Settings')
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.get('aws_access_key'),
            aws_secret_access_key=settings.get('aws_secret_key')
        )
        
        bucket = settings.get('s3_bucket')
        key = f"backups/{os.path.basename(backup_file)}"
        
        s3_client.upload_file(backup_file, bucket, key)
        return f"s3://{bucket}/{key}"
    
    def upload_to_gcs(self, backup_file):
        """Upload to Google Cloud Storage"""
        settings = frappe.get_single('Hosting Settings')
        client = gcs_storage.Client.from_service_account_json(
            settings.get('gcs_credentials_file')
        )
        
        bucket = client.bucket(settings.get('gcs_bucket'))
        blob = bucket.blob(f"backups/{os.path.basename(backup_file)}")
        blob.upload_from_filename(backup_file)
        
        return f"gs://{settings.get('gcs_bucket')}/backups/{os.path.basename(backup_file)}"
    
    def upload_to_dropbox(self, backup_file):
        """Upload to Dropbox"""
        settings = frappe.get_single('Hosting Settings')
        dbx = dropbox.Dropbox(settings.get('dropbox_access_token'))
        
        with open(backup_file, 'rb') as f:
            dbx.files_upload(f.read(), f"/backups/{os.path.basename(backup_file)}")
        
        return f"dropbox:/backups/{os.path.basename(backup_file)}"
    
    def restore_backup(self):
        """Restore backup to website"""
        try:
            if not self.file_path or not os.path.exists(self.file_path):
                frappe.throw("Backup file not found")
            
            restore_file_path = self.file_path
            is_decrypted = False
            
            # Decrypt if encrypted
            if self.is_encrypted:
                try:
                    from rpanel.hosting.backup_encryption import decrypt_backup
                    restore_file_path = decrypt_backup(self.file_path)
                    is_decrypted = True
                except Exception as e:
                    frappe.throw(f"Decryption failed: {str(e)}")
            
            website = frappe.get_doc('Hosted Website', self.website)
            
            try:
                if self.backup_type == 'Full':
                    self.restore_full_backup(website, restore_file_path)
                elif self.backup_type == 'Database Only':
                    self.restore_database_backup(website, restore_file_path)
                elif self.backup_type == 'Files Only':
                    self.restore_files_backup(website, restore_file_path)
            finally:
                # Clean up decrypted file
                if is_decrypted and os.path.exists(restore_file_path):
                    os.remove(restore_file_path)
            
            return {'success': True}
            
        except Exception as e:
            frappe.log_error(f"Backup restore failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def restore_full_backup(self, website, file_path):
        """Restore full backup"""
        # Extract backup
        cmd = f"tar -xzf {file_path} -C {website.site_path}"
        subprocess.run(shlex.split(cmd), check=True)
        
        # Restore database
        db_file = os.path.join(website.site_path, f"*_db.sql")
        # Secure: Password hidden from process list
        run_mysql_restore(
            database=website.db_name,
            input_file=db_file,
            user=website.db_user,
            password=website.db_password
        )
    
    def restore_database_backup(self, website, file_path):
        """Restore database backup"""
        # Secure: Password hidden from process list
        run_mysql_restore(
            database=website.db_name,
            input_file=file_path,
            user=website.db_user,
            password=website.db_password
        )
    
    def restore_files_backup(self, website, file_path):
        """Restore files backup"""
        cmd = f"tar -xzf {file_path} -C {website.site_path}"
        subprocess.run(shlex.split(cmd), check=True)


@frappe.whitelist()
def create_backup(website, backup_type='Full', upload_to_cloud=False, cloud_storage='None'):
    """Create a new backup"""
    if website == 'local_control_site':
        if "System Manager" not in frappe.get_roles():
            frappe.throw("Access Denied")
        # Trigger standard bench backup
        from frappe.utils.backups import new_backup
        new_backup(ignore_conf=False, force=True, verbose=False)
        return {'success': True, 'message': 'Backup started in background'}

    backup = frappe.get_doc({
        'doctype': 'Site Backup',
        'website': website,
        'backup_type': backup_type,
        'cloud_storage': cloud_storage if upload_to_cloud else 'None'
    })
    backup.insert()
    
    result = backup.create_backup()
    return result


@frappe.whitelist()
def restore_backup(backup_id):
    """Restore a backup"""
    backup = frappe.get_doc('Site Backup', backup_id)
    return backup.restore_backup()


@frappe.whitelist()
def delete_backup(backup_id):
    """Delete a backup file and record"""
    backup = frappe.get_doc('Site Backup', backup_id)
    
    # Delete file if exists
    if backup.file_path and os.path.exists(backup.file_path):
        os.remove(backup.file_path)
    
    # Delete record
    backup.delete()
    
    return {'success': True}

@frappe.whitelist()
def get_backups(website=None):
    """Alias for list_backups to match frontend call"""
    return list_backups(website)

@frappe.whitelist()
def list_backups(website_name=None):
    """List all backups, optionally filtered by website"""
    filters = {}
    if website_name:
        filters['website'] = website_name
    
    backups = frappe.get_all(
        'Site Backup',
        filters=filters,
        fields=['name', 'website', 'backup_type', 'backup_date', 'file_size', 'status', 'cloud_storage'],
        order_by='backup_date desc'
    )
    
    return backups


def schedule_backup(website_name, frequency='daily'):
    """Schedule automatic backups (called by cron)"""
    create_backup(website_name, 'Full', upload_to_cloud=True)
