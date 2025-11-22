# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe
import subprocess
import sys

def check_and_install_dependencies():
    """Check and install hosting module dependencies"""
    required_packages = [
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
    
    missing_packages = []
    
    # Check which packages are missing
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    # Install missing packages
    if missing_packages:
        print(f"\n{'='*60}")
        print("ROKCT Hosting Module: Installing dependencies...")
        print(f"{'='*60}\n")
        
        for package in missing_packages:
            try:
                print(f"Installing {package}...")
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', package
                ])
                print(f"✓ {package} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to install {package}: {str(e)}")
        
        print(f"\n{'='*60}")
        print("Dependency installation complete!")
        print(f"{'='*60}\n")
    else:
        print("\n✓ All hosting module dependencies are already installed\n")


def after_install():
    """Run after hosting module installation"""
    check_and_install_dependencies()
    
    # Create default alert templates
    try:
        frappe.get_attr('rpanel.hosting.doctype.alert_template.alert_template.create_default_templates')()
        print("✓ Created default alert templates")
    except Exception as e:
        print(f"Note: Could not create default templates: {str(e)}")


def after_migrate():
    """Run after migration"""
    check_and_install_dependencies()
