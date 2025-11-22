# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

"""
ModSecurity Manager

Manages ModSecurity Web Application Firewall configuration for RPanel websites.
Protects against: SQL Injection, XSS, File Inclusion, Command Injection, CSRF, etc.
"""

import frappe
import os
import subprocess
from pathlib import Path


class ModSecurityManager:
    """Manages ModSecurity WAF configuration"""
    
    def __init__(self):
        self.modsec_dir = Path('/etc/nginx/modsec')
        self.rules_dir = self.modsec_dir / 'rules'
        self.crs_dir = self.modsec_dir / 'coreruleset'
    
    def setup_modsecurity(self):
        """
        Initial setup of ModSecurity
        Installs OWASP Core Rule Set and creates base configuration
        """
        # Create directories
        self.modsec_dir.mkdir(parents=True, exist_ok=True)
        self.rules_dir.mkdir(exist_ok=True)
        
        # Download OWASP Core Rule Set if not exists
        if not self.crs_dir.exists():
            self._download_owasp_crs()
        
        # Create main ModSecurity config
        self._create_main_config()
        
        # Create RPanel-specific rules
        self._create_rpanel_rules()
        
        print("✓ ModSecurity configured successfully")
    
    def _download_owasp_crs(self):
        """Download OWASP ModSecurity Core Rule Set"""
        print("Downloading OWASP Core Rule Set...")
        
        subprocess.run([
            'wget', '-q',
            'https://github.com/coreruleset/coreruleset/archive/refs/tags/v3.3.5.tar.gz',
            '-O', '/tmp/crs.tar.gz'
        ], check=True)
        
        subprocess.run([
            'tar', 'xzf', '/tmp/crs.tar.gz',
            '-C', str(self.modsec_dir)
        ], check=True)
        
        # Rename to simpler name
        subprocess.run([
            'mv',
            str(self.modsec_dir / 'coreruleset-3.3.5'),
            str(self.crs_dir)
        ], check=True)
        
        # Copy setup file
        subprocess.run([
            'cp',
            str(self.crs_dir / 'crs-setup.conf.example'),
            str(self.crs_dir / 'crs-setup.conf')
        ], check=True)
        
        # Cleanup
        os.remove('/tmp/crs.tar.gz')
    
    def _create_main_config(self):
        """Create main ModSecurity configuration file"""
        config = """# ModSecurity Main Configuration
# Managed by RPanel - DO NOT EDIT MANUALLY

# Enable ModSecurity
SecRuleEngine On

# Request body handling
SecRequestBodyAccess On
SecRequestBodyLimit 13107200
SecRequestBodyNoFilesLimit 131072
SecRequestBodyLimitAction Reject

# Response body handling
SecResponseBodyAccess On
SecResponseBodyMimeType text/plain text/html text/xml
SecResponseBodyLimit 524288
SecResponseBodyLimitAction ProcessPartial

# Filesystem configuration
SecTmpDir /tmp/
SecDataDir /tmp/

# Debug log
SecDebugLog /var/log/nginx/modsec_debug.log
SecDebugLogLevel 0

# Audit log
SecAuditEngine RelevantOnly
SecAuditLogRelevantStatus "^(?:5|4(?!04))"
SecAuditLogParts ABIJDEFHZ
SecAuditLogType Serial
SecAuditLog /var/log/nginx/modsec_audit.log

# Upload handling
SecTmpSaveUploadedFiles On
SecUploadDir /tmp/
SecUploadKeepFiles Off

# Misc
SecArgumentSeparator &
SecCookieFormat 0
SecStatusEngine On

# Include OWASP CRS
Include /etc/nginx/modsec/coreruleset/crs-setup.conf
Include /etc/nginx/modsec/coreruleset/rules/*.conf

# Include RPanel custom rules
Include /etc/nginx/modsec/rules/*.conf
"""
        
        config_file = self.modsec_dir / 'main.conf'
        with open(config_file, 'w') as f:
            f.write(config)
        
        os.chmod(config_file, 0o644)
    
    def _create_rpanel_rules(self):
        """Create RPanel-specific ModSecurity rules"""
        rules = """# RPanel Custom ModSecurity Rules
# Additional protection for WordPress and common CMSs

# WordPress login protection
SecRule REQUEST_URI "@streq /wp-login.php" \\
    "id:1000,\\
    phase:1,\\
    t:none,\\
    pass,\\
    nolog,\\
    setvar:'tx.wordpress_login=1'"

# Block common WordPress attack patterns
SecRule REQUEST_URI "@rx /wp-content/uploads/.*\\.php" \\
    "id:1001,\\
    phase:1,\\
    t:none,\\
    deny,\\
    status:403,\\
    log,\\
    msg:'PHP file upload attempt blocked'"

# Protect against XML-RPC attacks
SecRule REQUEST_URI "@streq /xmlrpc.php" \\
    "id:1002,\\
    phase:1,\\
    t:none,\\
    deny,\\
    status:403,\\
    log,\\
    msg:'XML-RPC access blocked (use Application Passwords instead)'"

# Block user enumeration
SecRule REQUEST_URI "@rx \\?author=[0-9]+" \\
    "id:1003,\\
    phase:1,\\
    t:none,\\
    deny,\\
    status:403,\\
    log,\\
    msg:'WordPress user enumeration attempt blocked'"
"""
        
        rules_file = self.rules_dir / 'rpanel-custom.conf'
        with open(rules_file, 'w') as f:
            f.write(rules)
        
        os.chmod(rules_file, 0o644)
    
    def enable_for_website(self, domain):
        """
        Enable ModSecurity for a specific website
        
        Args:
            domain: Website domain
        """
        from rpanel.hosting.nginx_manager import NginxManager
        
        nginx_mgr = NginxManager()
        config_name = nginx_mgr.get_rpanel_config_name(domain)
        config_path = nginx_mgr.available_path / config_name
        
        if not config_path.exists():
            frappe.throw(f"Nginx config not found for {domain}")
        
        # Read current config
        with open(config_path, 'r') as f:
            config = f.read()
        
        # Check if ModSecurity already enabled
        if 'modsecurity on' in config:
            frappe.msgprint(f"ModSecurity already enabled for {domain}")
            return
        
        # Add ModSecurity directives after server_name
        modsec_config = """
    # ModSecurity Web Application Firewall
    modsecurity on;
    modsecurity_rules_file /etc/nginx/modsec/main.conf;
"""
        
        # Insert after server_name line
        lines = config.split('\n')
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if 'server_name' in line:
                new_lines.append(modsec_config)
        
        # Write updated config
        with open(config_path, 'w') as f:
            f.write('\n'.join(new_lines))
        
        # Test and reload Nginx
        nginx_mgr.test_and_reload()
        
        frappe.msgprint(f"ModSecurity enabled for {domain}")
    
    def disable_for_website(self, domain):
        """
        Disable ModSecurity for a specific website
        
        Args:
            domain: Website domain
        """
        from rpanel.hosting.nginx_manager import NginxManager
        
        nginx_mgr = NginxManager()
        config_name = nginx_mgr.get_rpanel_config_name(domain)
        config_path = nginx_mgr.available_path / config_name
        
        if not config_path.exists():
            frappe.throw(f"Nginx config not found for {domain}")
        
        # Read current config
        with open(config_path, 'r') as f:
            config = f.read()
        
        # Remove ModSecurity directives
        lines = config.split('\n')
        new_lines = []
        skip_next = 0
        
        for line in lines:
            if skip_next > 0:
                skip_next -= 1
                continue
            
            if 'ModSecurity Web Application Firewall' in line:
                skip_next = 2  # Skip next 2 lines (modsecurity on; modsecurity_rules_file)
                continue
            
            if 'modsecurity' not in line.lower():
                new_lines.append(line)
        
        # Write updated config
        with open(config_path, 'w') as f:
            f.write('\n'.join(new_lines))
        
        # Test and reload Nginx
        nginx_mgr.test_and_reload()
        
        frappe.msgprint(f"ModSecurity disabled for {domain}")
    
    def get_blocked_requests(self, domain=None, limit=100):
        """
        Get blocked requests from ModSecurity audit log
        
        Args:
            domain: Filter by domain (optional)
            limit: Maximum number of results
        
        Returns:
            list: Blocked request entries
        """
        audit_log = '/var/log/nginx/modsec_audit.log'
        
        if not os.path.exists(audit_log):
            return []
        
        # Parse audit log (simplified - full parsing would be more complex)
        blocked = []
        
        try:
            with open(audit_log, 'r') as f:
                lines = f.readlines()
                
                for line in lines[-limit:]:
                    if domain and domain not in line:
                        continue
                    
                    # Extract basic info (this is simplified)
                    if 'ModSecurity' in line:
                        blocked.append({
                            'timestamp': line[:23] if len(line) > 23 else '',
                            'message': line.strip()
                        })
        
        except Exception as e:
            frappe.log_error(f"Error reading ModSecurity audit log: {str(e)}")
        
        return blocked


# Convenience functions

def setup_modsecurity():
    """Setup ModSecurity (run during installation)"""
    manager = ModSecurityManager()
    manager.setup_modsecurity()


@frappe.whitelist()
def enable_modsecurity_for_website(domain):
    """Enable ModSecurity for a website (whitelisted for UI)"""
    manager = ModSecurityManager()
    manager.enable_for_website(domain)


@frappe.whitelist()
def disable_modsecurity_for_website(domain):
    """Disable ModSecurity for a website (whitelisted for UI)"""
    manager = ModSecurityManager()
    manager.disable_for_website(domain)


@frappe.whitelist()
def get_modsecurity_blocked_requests(domain=None, limit=100):
    """Get blocked requests (whitelisted for UI)"""
    manager = ModSecurityManager()
    return manager.get_blocked_requests(domain, limit)
