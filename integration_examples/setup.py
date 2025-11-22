"""
RPanel Integration: Auto-Install Hook
=====================================

Use this code in your custom Frappe app to automatically install RPanel on your control site.

How to use:
1. Copy this function to your app (e.g., `yourapp/setup.py`).
2. Add a hook in `hooks.py`:
   `after_install = "yourapp.setup.check_and_install_rpanel"`

"""

import frappe
import subprocess
import os
import requests
import sys
from frappe.installer import install_app as frappe_install_app

def get_latest_rpanel_release():
    """Fetch latest tag from GitHub"""
    try:
        response = requests.get('https://api.github.com/repos/RokctAI/rpanel/releases/latest', timeout=5)
        if response.status_code == 200:
            return response.json().get('tag_name')
    except Exception as e:
        print(f"Warning: Could not fetch RPanel release: {e}")
    return None

def check_and_install_rpanel():
    """
    Checks if RPanel is installed, and installs it if not.
    Only runs on 'control' sites.
    """
    # 1. Check if this is a control site (Customize this logic for your needs)
    is_control_site = frappe.local.site == "control" or frappe.conf.get('app_role') == 'control'
    
    if not is_control_site:
        return

    # 2. Check if already installed
    if 'rpanel' in frappe.get_installed_apps():
        return

    print("Installing RPanel...")
    
    try:
        bench_path = frappe.utils.get_bench_path()
        site = frappe.local.site
        
        # 3. Get App
        cmd = ['bench', 'get-app', 'https://github.com/RokctAI/rpanel.git']
        latest_tag = get_latest_rpanel_release()
        if latest_tag:
             cmd.extend(['--branch', latest_tag])
             
        subprocess.check_call(cmd, cwd=bench_path)
        
        # 4. Install App
        subprocess.check_call(['bench', '--site', site, 'install-app', 'rpanel'], cwd=bench_path)
        print("✓ RPanel installed successfully!")
        
    except Exception as e:
        frappe.log_error(f"RPanel Install Failed: {e}")
        print(f"✗ Failed to install RPanel: {e}")
