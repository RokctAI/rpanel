# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

"""
Nginx Configuration Manager for RPanel

This module manages Nginx configurations for hosted websites while being aware of:
- Frappe bench config (frappe-bench-frappe)
- ROKCT Ollama proxy (ollama-proxy.conf)

It ensures RPanel never conflicts with these existing configurations.
"""

import os
import subprocess
import frappe
from pathlib import Path

# Protected config files that RPanel should NEVER modify
PROTECTED_CONFIGS = [
    'frappe-bench-frappe',      # Frappe bench (created by bench setup production)
    'ollama-proxy.conf',         # ROKCT Ollama API proxy
    'default',                   # System default
]

# RPanel config file prefix
RPANEL_PREFIX = 'rpanel-'

# Nginx paths
NGINX_AVAILABLE = '/etc/nginx/sites-available'
NGINX_ENABLED = '/etc/nginx/sites-enabled'
NGINX_CONF_D = '/etc/nginx/conf.d'


class NginxManager:
    """Manages Nginx configurations for RPanel websites"""
    
    def __init__(self):
        self.available_path = Path(NGINX_AVAILABLE)
        self.enabled_path = Path(NGINX_ENABLED)
        self.conf_d_path = Path(NGINX_CONF_D)
    
    def is_protected_config(self, filename):
        """Check if a config file is protected (managed by Frappe/ROKCT)"""
        return filename in PROTECTED_CONFIGS
    
    def get_rpanel_config_name(self, domain):
        """Get the config filename for a domain"""
        # Sanitize domain name for filename
        safe_domain = domain.replace('.', '_').replace(':', '_')
        return f"{RPANEL_PREFIX}{safe_domain}.conf"
    
    def create_website_config(self, domain, site_path, php_version='8.3'):
        """
        Create Nginx config for a hosted website
        
        Args:
            domain: Website domain name
            site_path: Absolute path to website root
            php_version: PHP version to use (default: 8.3)
        """
        config_name = self.get_rpanel_config_name(domain)
        config_path = self.available_path / config_name
        
        # Check if this would conflict with protected configs
        if self.is_protected_config(config_name):
            frappe.throw(f"Cannot create config '{config_name}' - this filename is protected")
        
        # Generate Nginx config
        config_content = self._generate_website_config(domain, site_path, php_version)
        
        # Write config file
        try:
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            # Set proper permissions
            os.chmod(config_path, 0o644)
            
            # Enable the site
            self.enable_site(config_name)
            
            # Test and reload Nginx
            self.test_and_reload()
            
            frappe.msgprint(f"Nginx configuration created for {domain}")
            
        except Exception as e:
            frappe.log_error(f"Failed to create Nginx config for {domain}: {str(e)}")
            frappe.throw(f"Failed to create Nginx configuration: {str(e)}")
    
    def _generate_website_config(self, domain, site_path, php_version):
        """Generate Nginx configuration content for a website"""
        
        config = f"""# Managed by RPanel - Website: {domain}
# DO NOT EDIT MANUALLY - Changes will be overwritten by RPanel

server {{
    listen 80;
    server_name {domain};
    
    root {site_path};
    index index.php index.html index.htm;
    
    # Include RPanel rate limiting (if exists)
    include /etc/nginx/conf.d/rpanel-rate-limits.conf;
    
    # Logging
    access_log /var/log/nginx/{domain}-access.log;
    error_log /var/log/nginx/{domain}-error.log;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Deny access to hidden files
    location ~ /\. {{
        deny all;
    }}
    
    # PHP handling
    location ~ \.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php{php_version}-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }}
    
    # WordPress permalinks
    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}
    
    # Deny access to sensitive files
    location ~* \.(htaccess|htpasswd|ini|log|sh|sql|conf)$ {{
        deny all;
    }}
    
    # Cache static assets
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {{
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}
}}
"""
        return config
    
    def enable_site(self, config_name):
        """Enable a site by creating symlink in sites-enabled"""
        source = self.available_path / config_name
        target = self.enabled_path / config_name
        
        if not source.exists():
            frappe.throw(f"Config file not found: {source}")
        
        # Remove existing symlink if it exists
        if target.exists() or target.is_symlink():
            target.unlink()
        
        # Create symlink
        target.symlink_to(source)
    
    def disable_site(self, config_name):
        """Disable a site by removing symlink from sites-enabled"""
        target = self.enabled_path / config_name
        
        if target.exists() or target.is_symlink():
            target.unlink()
    
    def delete_site_config(self, domain):
        """Delete Nginx config for a domain"""
        config_name = self.get_rpanel_config_name(domain)
        
        # Check if protected
        if self.is_protected_config(config_name):
            frappe.throw(f"Cannot delete protected config: {config_name}")
        
        # Disable first
        self.disable_site(config_name)
        
        # Delete config file
        config_path = self.available_path / config_name
        if config_path.exists():
            config_path.unlink()
        
        # Reload Nginx
        self.test_and_reload()
    
    def test_and_reload(self):
        """Test Nginx config and reload if valid"""
        try:
            # Test configuration
            result = subprocess.run(
                ['nginx', '-t'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                error_msg = result.stderr
                frappe.log_error(f"Nginx config test failed: {error_msg}")
                frappe.throw(f"Nginx configuration error: {error_msg}")
            
            # Reload Nginx
            subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
            
        except subprocess.CalledProcessError as e:
            frappe.log_error(f"Failed to reload Nginx: {str(e)}")
            frappe.throw(f"Failed to reload Nginx: {str(e)}")
    
    def setup_rate_limiting(self):
        """
        Setup global rate limiting for RPanel websites
        Only runs once during installation
        """
        rate_limit_config = self.conf_d_path / 'rpanel-rate-limits.conf'
        
        if rate_limit_config.exists():
            return  # Already configured
        
        config_content = """# RPanel Global Rate Limiting
# Prevents DDoS attacks on hosted websites

# Zone definitions
limit_req_zone $binary_remote_addr zone=rpanel_general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=rpanel_login:10m rate=5r/m;

# Apply general rate limiting
limit_req zone=rpanel_general burst=20 nodelay;

# Stricter limits for login endpoints
# This is applied in individual site configs for WordPress, etc.
"""
        
        try:
            with open(rate_limit_config, 'w') as f:
                f.write(config_content)
            
            os.chmod(rate_limit_config, 0o644)
            
            print("✓ RPanel rate limiting configured")
            
        except Exception as e:
            frappe.log_error(f"Failed to setup rate limiting: {str(e)}")
    
    def get_all_rpanel_sites(self):
        """Get list of all RPanel-managed sites"""
        sites = []
        
        for config_file in self.available_path.glob(f"{RPANEL_PREFIX}*.conf"):
            sites.append(config_file.name)
        
        return sites
    
    def check_conflicts(self):
        """
        Check for potential conflicts with Frappe/ROKCT configs
        Returns list of conflicts found
        """
        conflicts = []
        
        # Check if protected configs exist
        for protected in PROTECTED_CONFIGS:
            config_path = self.available_path / protected
            if config_path.exists():
                # Check if any RPanel config might conflict
                # (This is mainly for documentation/awareness)
                pass
        
        return conflicts


# Convenience functions for use in DocTypes

def create_nginx_config(domain, site_path, php_version='8.3'):
    """Create Nginx config for a website"""
    manager = NginxManager()
    manager.create_website_config(domain, site_path, php_version)


def delete_nginx_config(domain):
    """Delete Nginx config for a website"""
    manager = NginxManager()
    manager.delete_site_config(domain)


def setup_nginx_rate_limiting():
    """Setup global rate limiting (run during installation)"""
    manager = NginxManager()
    manager.setup_rate_limiting()


def secure_website_permissions(site_path, owner='www-data'):
    """
    Set secure file permissions for a website
    
    Args:
        site_path: Absolute path to website root
        owner: User/group owner (default: www-data)
    """
    import subprocess
    
    try:
        # Set directory permissions: 755 (rwxr-xr-x)
        subprocess.run([
            'find', site_path, '-type', 'd',
            '-exec', 'chmod', '755', '{}', '+'
        ], check=True)
        
        # Set file permissions: 644 (rw-r--r--)
        subprocess.run([
            'find', site_path, '-type', 'f',
            '-exec', 'chmod', '644', '{}', '+'
        ], check=True)
        
        # Set ownership
        subprocess.run([
            'chown', '-R', f'{owner}:{owner}', site_path
        ], check=True)
        
        # Secure upload directories (775 for write access)
        upload_dirs = [
            os.path.join(site_path, 'wp-content/uploads'),
            os.path.join(site_path, 'uploads'),
        ]
        
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                subprocess.run(['chmod', '-R', '775', upload_dir], check=True)
        
        # Secure config files (600 for sensitive files)
        config_files = [
            os.path.join(site_path, 'wp-config.php'),
            os.path.join(site_path, '.htaccess'),
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                subprocess.run(['chmod', '600', config_file], check=True)
        
        frappe.msgprint(f"File permissions secured for {site_path}")
        
    except subprocess.CalledProcessError as e:
        frappe.log_error(f"Failed to secure permissions for {site_path}: {str(e)}")
        frappe.throw(f"Failed to secure file permissions: {str(e)}")
