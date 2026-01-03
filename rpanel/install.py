# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import subprocess
import sys

def after_install():
    """Run after RPanel installation"""
    print("Installing RPanel dependencies...")
    check_and_install_system_dependencies()
    install_dependencies()
    create_default_settings()
    
    # Setup security features
    print("Configuring security features...")
    setup_security_features()
    
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


def check_and_install_system_dependencies():
    """
    Check for and install missing system dependencies when RPanel is installed via bench install-app
    Gets MariaDB password from common_site_config.json
    Reads dependency list from dependencies.json (single source of truth)
    """
    import os
    import json
    
    print("\n=== Checking System Dependencies ===")
    
    # Load dependencies from single source of truth
    try:
        deps_file = os.path.join(os.path.dirname(__file__), '..', 'dependencies.json')
        with open(deps_file, 'r') as f:
            all_deps = json.load(f)
        
        # Get system dependencies (hosting services)
        dependencies = all_deps.get('system_dependencies', {})
    except Exception as e:
        print(f"Error: Could not load dependencies.json: {str(e)}")
        return
    
    # Get MariaDB root password from common_site_config.json
    try:
        bench_path = frappe.utils.get_bench_path()
        config_path = os.path.join(bench_path, 'sites', 'common_site_config.json')
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        db_password = config.get('db_password') or config.get('root_password', '')
    except Exception as e:
        print(f"Warning: Could not read MariaDB password from config: {str(e)}")
        db_password = ''
    
    # Check which dependencies are missing
    missing_deps = []
    
    for dep_name, dep_info in dependencies.items():
        try:
            result = subprocess.run(dep_info['check'], shell=True, capture_output=True)
            if result.returncode != 0:
                missing_deps.append(dep_name)
            else:
                print(f"✓ {dep_name} is installed")
        except Exception:
            missing_deps.append(dep_name)
    
    if not missing_deps:
        print("✓ All system dependencies are installed")
        return
    
    # Auto-install missing dependencies
    print(f"\nMissing dependencies: {', '.join(missing_deps)}")
    print("Installing missing dependencies automatically...\n")
    
    # Update package list first
    try:
        subprocess.run('sudo apt-get update', shell=True, check=True)
    except Exception as e:
        print(f"Warning: apt-get update failed: {str(e)}")
    
    # Install each missing dependency
    for dep_name in missing_deps:
        if dep_name in dependencies:
            dep_info = dependencies[dep_name]
            print(f"{dep_name} is missing, installing...")
            try:
                # Add sudo to the installation command
                install_cmd = f"sudo {dep_info['install']}"
                subprocess.run(install_cmd, shell=True, check=True)
                print(f"✓ {dep_name} installed successfully\n")
            except Exception as e:
                print(f"✗ Failed to install {dep_name}: {str(e)}")
                print(f"  You may need to install it manually: {install_cmd}\n")


def setup_security_features():
    """Setup security features after installation"""
    try:
        # Setup Nginx rate limiting
        from rpanel.hosting.nginx_manager import setup_nginx_rate_limiting
        setup_nginx_rate_limiting()
        print("✓ Nginx rate limiting configured")
    except Exception as e:
        print(f"Warning: Failed to setup Nginx rate limiting: {str(e)}")
    
    try:
        # Setup ModSecurity if installed
        result = subprocess.run('nginx -V 2>&1 | grep -q modsecurity', shell=True)
        if result.returncode == 0:
            from rpanel.hosting.modsecurity_manager import setup_modsecurity
            setup_modsecurity()
            print("✓ ModSecurity WAF configured")
        else:
            print("ℹ ModSecurity not installed, skipping WAF setup")
    except Exception as e:
        print(f"Warning: Failed to setup ModSecurity: {str(e)}")
    
    print("\n✓ System dependency installation complete")
