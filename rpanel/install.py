# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import subprocess
import sys

def after_install():
    """Run after RPanel installation"""
    import os
    
    if os.environ.get('CI') or os.environ.get('NON_INTERACTIVE'):
        print("CI/Non-Interactive environment detected: Skipping system dependency installs in after_install")
    else:
        print("Installing RPanel dependencies...")
        check_and_install_system_dependencies()
        install_dependencies()
    
    create_default_settings()
    
    # Setup security features
    if not (os.environ.get('CI') or os.environ.get('NON_INTERACTIVE')):
        print("Configuring security features...")
        setup_security_features()
    
    # Setup pgvector
    print("Configuring Database Extensions...")
    setup_vector_extension()
    
    print("RPanel installed successfully!")

def after_migrate():
    """Run after migrations"""
    check_dependencies()
    setup_vector_extension()

def setup_vector_extension():
    """
    Enables the pgvector extension if not already enabled.
    """
    try:
        frappe.db.sql("CREATE EXTENSION IF NOT EXISTS vector")
        frappe.db.commit()
        return True
    except Exception as e:
        frappe.db.rollback()
        # Log purely as warning, don't crash install
        print(f"⚠️ Failed to enable pgvector: {e}")
        return False

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
    
    # OVERRIDE: Force correct ModSecurity package for Ubuntu 24.04
    # This ensures we use the correct package even if dependencies.json is reverted by update
    if 'modsecurity' in dependencies:
        dependencies['modsecurity'].update({
            'check': "dpkg -l | grep -q libnginx-mod-http-modsecurity",
            'install': "apt-get install -y libnginx-mod-http-modsecurity"
        })
    
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
                # Intelligent sudo injection for chained commands and pipes
                cmd = dep_info['install']
                
                # Handle && chains - add sudo to each part
                parts = cmd.split('&&')
                sudo_parts = []
                for part in parts:
                    part = part.strip()
                    # Handle pipes within parts
                    if '|' in part:
                        pipe_parts = part.split('|')
                            # Add sudo after pipe if not present
                        part = '|'.join([p if i==0 else f" sudo {p.strip()}" for i, p in enumerate(pipe_parts)])
                    
                    # Add sudo if not present (handling env as well)
                    if not part.startswith('sudo'):
                        sudo_parts.append(f"sudo {part}")
                    else:
                        sudo_parts.append(part)
                
                install_cmd = ' && '.join(sudo_parts)
                
                print(f"Executing: {install_cmd}")
                subprocess.run(install_cmd, shell=True, check=True)
                
                # Special handling for packages that might start apache2
                if dep_name in ['roundcube', 'phpmyadmin']:
                    subprocess.run("sudo systemctl stop apache2 || true", shell=True)
                    subprocess.run("sudo systemctl disable apache2 || true", shell=True)
                    
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
        # Check for compiled module OR Ubuntu package
        result = subprocess.run('nginx -V 2>&1 | grep -q modsecurity', shell=True)
        pkg_result = subprocess.run('dpkg -l | grep -q libnginx-mod-http-modsecurity', shell=True)
        
        if result.returncode == 0 or pkg_result.returncode == 0:
            from rpanel.hosting.modsecurity_manager import setup_modsecurity
            setup_modsecurity()
            print("✓ ModSecurity WAF configured")
        else:
            print("ℹ ModSecurity not installed, skipping WAF setup")
    except Exception as e:
        print(f"Warning: Failed to setup ModSecurity: {str(e)}")
    
    print("\n✓ System dependency installation complete")
    
    # Final check: Ensure Apache is dead and Nginx is alive
    # This is critical because some packages (phpmyadmin/roundcube) might restart apache at the end of their install scripts
    print("\n=== Verifying Web Server Status ===")
    try:
        print("Configuring Apache for safe coexistence (Port 8080)...")
        # Change Listen 80 to Listen 8080 in ports.conf
        subprocess.run(["sudo", "sed", "-i", "s/Listen 80/Listen 8080/g", "/etc/apache2/ports.conf"], check=False)
        # Change <VirtualHost *:80> to <VirtualHost *:8080> in default site
        subprocess.run(["sudo", "sed", "-i", "s/<VirtualHost \*:80>/<VirtualHost \*:8080>/g", "/etc/apache2/sites-available/000-default.conf"], check=False)
        
        print("Stopping Apache2 service...")
        subprocess.run("sudo systemctl stop apache2 || true", shell=True)
        subprocess.run("sudo systemctl disable apache2 || true", shell=True)
        
        print("Restarting Nginx service...")
        subprocess.run("sudo systemctl restart nginx", shell=True, check=True)
        print("✓ Nginx restarted successfully (Port 80 reclaimed)")
    except Exception as e:
        print(f"Warning: Could not restart Nginx: {e}")
        print("Please run manually: sudo systemctl restart nginx")
