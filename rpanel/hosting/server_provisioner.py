# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe
import subprocess
from rpanel.hosting.doctype.hosting_server.hosting_server import execute_remote_command

@frappe.whitelist()
def provision_server(server_name):
    """
    Automatically install and configure all required services on a remote server
    - Nginx
    - MariaDB
    - PHP-FPM (multiple versions)
    - phpMyAdmin
    - Certbot (Let's Encrypt)
    - Exim4 (email)
    - Roundcube (webmail)
    - WordPress CLI
    - ClamAV (malware scanner)
    - Fail2Ban
    - UFW (firewall)
    """
    
    server = frappe.get_doc('Hosting Server', server_name)
    
    # Smart installation script - checks and installs only missing services
    install_script = """#!/bin/bash
set -e

echo "=== ROKCT Hosting Server Provisioning ==="
echo "Checking installed services and installing missing ones..."

# Update system
echo "[1/12] Updating system packages..."
apt update && apt upgrade -y

# Install Nginx (if not installed)
echo "[2/12] Checking Nginx..."
if ! command -v nginx &> /dev/null; then
    echo "Installing Nginx..."
    apt install -y nginx
    systemctl enable nginx
    systemctl start nginx
else
    echo "✓ Nginx already installed"
fi

# Install MariaDB (if not installed)
echo "[3/12] Checking MariaDB..."
if ! command -v mysql &> /dev/null; then
    echo "Installing MariaDB..."
    apt install -y mariadb-server mariadb-client
    systemctl enable mariadb
    systemctl start mariadb
    # Auto-secure MariaDB
    mysql -e "DELETE FROM mysql.user WHERE User='';"
    mysql -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
    mysql -e "DROP DATABASE IF EXISTS test;"
    mysql -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';"
    mysql -e "FLUSH PRIVILEGES;"
else
    echo "✓ MariaDB already installed"
fi

# Install PHP versions (if not installed)
echo "[4/12] Checking PHP versions..."
if ! dpkg -l | grep -q php8.3-fpm; then
    echo "Installing PHP 8.3..."
    apt install -y software-properties-common
    add-apt-repository -y ppa:ondrej/php
    apt update
    apt install -y php8.3-fpm php8.3-mysql php8.3-curl php8.3-gd php8.3-mbstring php8.3-xml php8.3-zip
    systemctl enable php8.3-fpm
    systemctl start php8.3-fpm
else
    echo "✓ PHP 8.3 already installed"
fi

if ! dpkg -l | grep -q php8.2-fpm; then
    echo "Installing PHP 8.2..."
    apt install -y php8.2-fpm php8.2-mysql php8.2-curl php8.2-gd php8.2-mbstring php8.2-xml php8.2-zip
    systemctl enable php8.2-fpm
    systemctl start php8.2-fpm
else
    echo "✓ PHP 8.2 already installed"
fi

if ! dpkg -l | grep -q php8.1-fpm; then
    echo "Installing PHP 8.1..."
    apt install -y php8.1-fpm php8.1-mysql php8.1-curl php8.1-gd php8.1-mbstring php8.1-xml php8.1-zip
    systemctl enable php8.1-fpm
    systemctl start php8.1-fpm
else
    echo "✓ PHP 8.1 already installed"
fi

# Install Certbot (if not installed)
echo "[5/12] Checking Certbot..."
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    apt install -y certbot python3-certbot-nginx
else
    echo "✓ Certbot already installed"
fi

# Install Exim4 (if not installed)
echo "[6/12] Checking Exim4..."
if ! dpkg -l | grep -q exim4; then
    echo "Installing Exim4..."
    apt install -y exim4 exim4-daemon-heavy dovecot-core dovecot-imapd dovecot-pop3d
    # Configure Exim4
    debconf-set-selections <<EOF
exim4-config exim4/dc_eximconfig_configtype select internet site; mail is sent and received directly using SMTP
exim4-config exim4/dc_other_hostnames string
exim4-config exim4/dc_local_interfaces string 127.0.0.1 ; ::1
EOF
    dpkg-reconfigure -f noninteractive exim4-config
    systemctl enable exim4
    systemctl enable dovecot
    systemctl start exim4
    systemctl start dovecot
else
    echo "✓ Exim4 already installed"
fi

# Install Roundcube (if not installed)
echo "[7/12] Checking Roundcube..."
if ! dpkg -l | grep -q roundcube; then
    echo "Installing Roundcube..."
    DEBIAN_FRONTEND=noninteractive apt install -y roundcube roundcube-core roundcube-mysql roundcube-plugins
else
    echo "✓ Roundcube already installed"
fi

# Install phpMyAdmin (if not installed)
echo "[8/12] Checking phpMyAdmin..."
if [ ! -d "/usr/share/phpmyadmin" ]; then
    echo "Installing phpMyAdmin..."
    DEBIAN_FRONTEND=noninteractive apt install -y phpmyadmin
else
    echo "✓ phpMyAdmin already installed"
fi

# Install WP-CLI (if not installed)
echo "[9/12] Checking WP-CLI..."
if ! command -v wp &> /dev/null; then
    echo "Installing WP-CLI..."
    curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
    chmod +x wp-cli.phar
    mv wp-cli.phar /usr/local/bin/wp
else
    echo "✓ WP-CLI already installed"
fi

# Install ClamAV (if not installed)
echo "[10/12] Checking ClamAV..."
if ! command -v clamscan &> /dev/null; then
    echo "Installing ClamAV..."
    apt install -y clamav clamav-daemon
    systemctl stop clamav-freshclam
    freshclam
    systemctl start clamav-freshclam
    systemctl enable clamav-daemon
    systemctl start clamav-daemon
else
    echo "✓ ClamAV already installed"
fi

# Install Fail2Ban (if not installed)
echo "[11/12] Checking Fail2Ban..."
if ! command -v fail2ban-client &> /dev/null; then
    echo "Installing Fail2Ban..."
    apt install -y fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban
else
    echo "✓ Fail2Ban already installed"
fi

# Install UFW (if not installed)
echo "[12/12] Checking UFW..."
if ! command -v ufw &> /dev/null; then
    echo "Installing UFW..."
    apt install -y ufw
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow http
    ufw allow https
    ufw allow 'Nginx Full'
    echo "y" | ufw enable
else
    echo "✓ UFW already installed"
    # Ensure firewall rules are set
    ufw allow ssh 2>/dev/null || true
    ufw allow http 2>/dev/null || true
    ufw allow https 2>/dev/null || true
fi

# Create directory structure (if not exists)
echo "Setting up directory structure..."
mkdir -p /var/www
mkdir -p /var/backups/websites
mkdir -p /var/lib/rokct/hosting/cache

# Set permissions
chown -R www-data:www-data /var/www
chmod 755 /var/www

echo ""
echo "=== Provisioning Complete! ==="
echo "Server is ready for hosting!"
echo ""
echo "Installed/Verified services:"
echo "  ✓ Nginx"
echo "  ✓ MariaDB"
echo "  ✓ PHP (8.3, 8.2, 8.1)"
echo "  ✓ phpMyAdmin"
echo "  ✓ Certbot (Let's Encrypt)"
echo "  ✓ Exim4 + Dovecot (Email)"
echo "  ✓ Roundcube (Webmail)"
echo "  ✓ WP-CLI"
echo "  ✓ ClamAV (Malware Scanner)"
echo "  ✓ Fail2Ban"
echo "  ✓ UFW (Firewall)"
"""
    
    try:
        # Execute installation script on remote server
        frappe.msgprint("Starting server provisioning... This may take 10-15 minutes.")
        
        result = execute_remote_command(
            server_name=server_name,
            command=install_script,
            timeout=1800  # 30 minutes timeout
        )
        
        if result.get('success'):
            # Update server status
            server.db_set('provisioned', 1)
            server.db_set('health_status', 'Healthy')
            
            frappe.msgprint(f"""
                <h3>✅ Server Provisioned Successfully!</h3>
                <p>All services installed and configured on <b>{server.server_name}</b></p>
                <p>The server is now ready to host websites.</p>
            """)
            
            return {
                'success': True,
                'message': 'Server provisioned successfully',
                'output': result.get('output')
            }
        else:
            frappe.throw(f"Provisioning failed: {result.get('error')}")
            
    except Exception as e:
        frappe.log_error(f"Server provisioning failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def check_server_services(server_name):
    """Check which services are installed on the server"""
    
    check_script = """
    echo "Checking installed services..."
    
    services=("nginx" "mariadb" "php8.3-fpm" "php8.2-fpm" "exim4" "certbot" "fail2ban" "ufw")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet $service 2>/dev/null || command -v $service &> /dev/null; then
            echo "$service: INSTALLED"
        else
            echo "$service: NOT INSTALLED"
        fi
    done
    
    # Check WP-CLI
    if command -v wp &> /dev/null; then
        echo "wp-cli: INSTALLED"
    else
        echo "wp-cli: NOT INSTALLED"
    fi
    
    # Check phpMyAdmin
    if [ -d "/usr/share/phpmyadmin" ]; then
        echo "phpmyadmin: INSTALLED"
    else
        echo "phpmyadmin: NOT INSTALLED"
    fi
    """
    
    result = execute_remote_command(server_name, check_script)
    
    if result.get('success'):
        return {
            'success': True,
            'services': result.get('output')
        }
    else:
        return {'success': False, 'error': result.get('error')}
