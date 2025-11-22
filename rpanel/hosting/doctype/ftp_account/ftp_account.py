# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import subprocess
import crypt
import os

class FTPAccount(Document):
    def on_insert(self):
        """Create FTP user on system"""
        self.create_ftp_user()
    
    def on_trash(self):
        """Delete FTP user from system"""
        self.delete_ftp_user()
    
    def create_ftp_user(self):
        """Create system FTP user"""
        try:
            # Create user with encrypted password
            encrypted_password = crypt.crypt(self.get_password('password'), crypt.METHOD_SHA512)
            
            # Create user
            cmd = f"useradd -m -d {self.home_directory} -s /bin/bash {self.username}"
            subprocess.run(cmd, shell=True, check=True)
            
            # Set password
            cmd = f"echo '{self.username}:{self.get_password('password')}' | chpasswd"
            subprocess.run(cmd, shell=True, check=True)
            
            # Set permissions
            subprocess.run(f"chown -R {self.username}:www-data {self.home_directory}", shell=True, check=True)
            subprocess.run(f"chmod 755 {self.home_directory}", shell=True, check=True)
            
            # Add to vsftpd user list
            with open('/etc/vsftpd.userlist', 'a') as f:
                f.write(f"{self.username}\n")
            
            # Restart FTP service
            subprocess.run(['systemctl', 'restart', 'vsftpd'], check=True)
            
        except Exception as e:
            frappe.log_error(f"FTP user creation failed: {str(e)}")
    
    def delete_ftp_user(self):
        """Delete system FTP user"""
        try:
            # Delete user
            cmd = f"userdel -r {self.username}"
            subprocess.run(cmd, shell=True, check=True)
            
            # Remove from vsftpd user list
            with open('/etc/vsftpd.userlist', 'r') as f:
                lines = f.readlines()
            with open('/etc/vsftpd.userlist', 'w') as f:
                for line in lines:
                    if line.strip() != self.username:
                        f.write(line)
            
            # Restart FTP service
            subprocess.run(['systemctl', 'restart', 'vsftpd'], check=True)
            
        except Exception as e:
            frappe.log_error(f"FTP user deletion failed: {str(e)}")


@frappe.whitelist()
def get_ftp_logs(username, lines=50):
    """Get FTP connection logs for user"""
    try:
        cmd = f"grep '{username}' /var/log/vsftpd.log | tail -n {lines}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        return {'success': True, 'logs': result.stdout}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def test_ftp_connection(username, password):
    """Test FTP connection"""
    try:
        import ftplib
        ftp = ftplib.FTP('localhost')
        ftp.login(username, password)
        ftp.quit()
        
        return {'success': True, 'message': 'Connection successful'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
