# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe
import subprocess
import sys

def after_install():
    """Run after RPanel installation"""
    print("Installing RPanel dependencies...")
    install_dependencies()
    create_default_settings()
    print("RPanel installed successfully!")

def after_migrate():
    """Run after migrations"""
    check_dependencies()

def install_dependencies():
    """Install Python dependencies"""
    dependencies = [
        'croniter',
        'boto3',
        'google-cloud-storage',
        'dropbox',
        'dnspython',
        'paramiko',
        'google-auth',
        'google-auth-oauthlib',
        'google-auth-httplib2',
        'google-api-python-client'
    ]
    
    for dep in dependencies:
        try:
            # Try to import the dependency
            module_name = dep.replace('-', '_')
            __import__(module_name)
            print(f"✓ {dep} already installed")
        except ImportError:
            print(f"Installing {dep}...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep])
                print(f"✓ {dep} installed successfully")
            except Exception as e:
                print(f"✗ Failed to install {dep}: {str(e)}")

def check_dependencies():
    """Check if all dependencies are installed"""
    dependencies = [
        'croniter',
        'boto3',
        'google-cloud-storage',
        'dropbox',
        'dnspython',
        'paramiko'
    ]
    
    missing = []
    for dep in dependencies:
        try:
            module_name = dep.replace('-', '_')
            __import__(module_name)
        except ImportError:
            missing.append(dep)
    
    if missing:
        print(f"Warning: Missing dependencies: {', '.join(missing)}")
        print("Run: bench --site [site-name] migrate to install them")

def create_default_settings():
    """Create default Hosting Settings"""
    if not frappe.db.exists('Hosting Settings', 'Hosting Settings'):
        try:
            settings = frappe.get_doc({
                'doctype': 'Hosting Settings',
                'web_root_path': '/var/www',
                'default_php_version': '8.2',
                'enable_auto_ssl': 1,
                'enable_auto_backups': 1
            })
            settings.insert(ignore_permissions=True)
            frappe.db.commit()
            print("✓ Default Hosting Settings created")
        except Exception as e:
            print(f"Note: Could not create default settings: {str(e)}")
