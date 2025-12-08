"""
ROKCT Integration Example - RPanel Production Installation
===========================================================

This file shows how to integrate RPanel into ROKCT using stable production releases.

INTEGRATION INSTRUCTIONS:
------------------------

1. **Add to ROKCT's requirements.txt:**
   ```
   requests
   ```

2. **Update rokct/hosting/__init__.py:**
   - Copy the `get_latest_rpanel_release()` function below
   - Replace the existing `check_and_install_rpanel()` function with the one below

3. **Update rokct/hooks.py:**
   Ensure you have:
   ```python
   after_install = "rokct.hosting.check_and_install_rpanel"
   on_migrate = "rokct.hosting.check_and_install_rpanel"
   ```

4. **Test the integration:**
   ```bash
   # On a control site
   bench --site control.site install-app rokct
   # RPanel should auto-install using the latest stable release
   ```

WHAT THIS DOES:
---------------
- Fetches the latest RPanel release tag from GitHub (e.g., v1.5.0)
- Installs RPanel using `bench get-app --branch v1.5.0`
- Ensures production stability by using tested releases
- Falls back to main branch if GitHub API is unavailable

CODE TO COPY:
-------------
"""

import frappe
import subprocess
import os
import json
import requests

@frappe.whitelist()
def sync_client_with_subscription(client_name, subscription_plan):
    """
    Sync hosting client quotas with ROKCT subscription plan
    
    Args:
        client_name: Name of the Hosting Client
        subscription_plan: Name of the Subscription Plan
    """
    try:
        client = frappe.get_doc('Hosting Client', client_name)
        plan = frappe.get_doc('Subscription Plan', subscription_plan)
        
        # Update quotas based on subscription
        if hasattr(plan, 'max_websites'):
            client.max_websites = plan.max_websites
        
        if hasattr(plan, 'max_storage'):
            client.max_storage_gb = plan.max_storage
        
        if hasattr(plan, 'max_databases'):
            client.max_databases = plan.max_databases
        
        client.save()
        frappe.db.commit()
        
        return {'success': True, 'message': 'Client synced with subscription'}
        
    except Exception as e:
        frappe.log_error(f"Failed to sync client with subscription: {str(e)}")
        return {'success': False, 'error': str(e)}


def get_latest_rpanel_release():
    """
    Fetch the latest RPanel release tag from GitHub API
    Returns: tag name (e.g., 'v1.5.0') or None
    """
    try:
        response = requests.get(
            'https://api.github.com/repos/RokctAI/rpanel/releases/latest',
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('tag_name')
    except Exception as e:
        frappe.log_error(f"Failed to fetch latest RPanel release: {str(e)}")
    return None


def check_and_install_rpanel():
    """
    Check if RPanel is installed, and install it if not.
    Uses latest stable release for production deployments.
    Only runs on control sites (app_role = 'control')
    """
    # Check if this is a control site
    app_role = frappe.conf.get('app_role', 'tenant')
    
    if app_role != 'control':
        # Not a control site, skip RPanel installation
        return
    
    # Check if RPanel is already installed
    installed_apps = frappe.get_installed_apps()
    
    if 'rpanel' in installed_apps:
        print("✓ RPanel is already installed")
        return
    
    print("RPanel not found. Installing latest stable release...")
    
    try:
        bench_path = frappe.utils.get_bench_path()
        site = frappe.local.site
        
        # Get latest release tag
        latest_tag = get_latest_rpanel_release()
        
        if latest_tag:
            print(f"Installing RPanel {latest_tag}...")
            # Use bench get-app with specific tag for production stability
            subprocess.check_call([
                'bench', 'get-app',
                'https://github.com/RokctAI/rpanel.git',
                '--branch', latest_tag
            ], cwd=bench_path)
        else:
            print("Could not fetch latest release, using main branch...")
            # Fallback to main branch
            subprocess.check_call([
                'bench', 'get-app',
                'https://github.com/RokctAI/rpanel.git'
            ], cwd=bench_path)
        
        # Install RPanel app on the site
        print(f"Installing RPanel on site: {site}...")
        subprocess.check_call([
            'bench', '--site', site, 'install-app', 'rpanel'
        ], cwd=bench_path)
        
        print("✓ RPanel installed successfully!")
        
    except subprocess.CalledProcessError as e:
        frappe.log_error(f"Failed to install RPanel: {str(e)}", "RPanel Installation Error")
        print(f"✗ Failed to install RPanel: {str(e)}")
    except Exception as e:
        frappe.log_error(f"Error during RPanel installation: {str(e)}", "RPanel Installation Error")
        print(f"✗ Error: {str(e)}")


# ... rest of the integration code (sync functions, etc.)
