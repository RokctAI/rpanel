# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import subprocess
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
            # 1. Create user
            # Avoid shell=True to prevent injection and separate args safely
            subprocess.run([
                "useradd", 
                "-m", 
                "-d", self.home_directory, 
                "-s", "/bin/bash", 
                self.username
            ], check=True)
            
            # 2. Set password SECURELY
            # Pass data via stdin (input=...) instead of echo.
            # This keeps the password hidden from process lists (ps aux)
            payload = f"{self.username}:{self.get_password('password')}"
            subprocess.run(
                ['chpasswd'], 
                input=payload, 
                text=True, 
                check=True
            )
            
            # 3. Set permissions
            subprocess.run(["chown", "-R", f"{self.username}:www-data", self.home_directory], check=True)
            subprocess.run(["chmod", "755", self.home_directory], check=True)
            
            # 4. Add to vsftpd user list
            with open('/etc/vsftpd.userlist', 'a') as f:
                f.write(f"{self.username}\n")
            
            # 5. Restart FTP service
            subprocess.run(['systemctl', 'restart', 'vsftpd'], check=True)
            
        except subprocess.CalledProcessError as e:
            frappe.log_error(f"System command failed: {e}")
            frappe.throw("Failed to setup FTP user. Check logs.")
        except Exception as e:
            frappe.log_error(f"FTP user creation failed: {str(e)}")
            frappe.throw("An error occurred while creating the FTP account.")
    
    def delete_ftp_user(self):
        """Delete system FTP user"""
        try:
            # Delete user
            subprocess.run(["userdel", "-r", self.username], check=True)
            
            # Remove from vsftpd user list
            if os.path.exists('/etc/vsftpd.userlist'):
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
        # Pure Python file read — eliminates shell injection risk entirely
        log_path = '/var/log/vsftpd.log'
        if not os.path.exists(log_path):
            return {'success': True, 'logs': ''}
        with open(log_path, 'r') as f:
            matching = [line for line in f if username in line]
        output = ''.join(matching[-int(lines):])
        return {'success': True, 'logs': output}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def test_ftp_connection(username, password):
    """Test FTP connection"""
    try:
        import ftplib  # nosec B402 — FTP is the intentional purpose of this module
        ftp = ftplib.FTP('localhost')  # nosec B321
        ftp.login(username, password)
        ftp.quit()
        
        return {'success': True, 'message': 'Connection successful'}
    except Exception as e:
        return {'success': False, 'error': str(e)}