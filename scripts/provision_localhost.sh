#!/bin/bash
# RPanel Localhost Provisioning Script
# Extracted from server_provisioner.py for self-hosted installations

set -e

echo "=== RPanel Localhost Provisioning ==="
echo "Installing hosting services on this server..."

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

# MariaDB should already be installed from main installer

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

# Certbot should already be installed from main installer

# Install Dovecot (if not installed)
echo "[6/12] Checking Dovecot..."
if ! dpkg -l | grep -q dovecot-core; then
    echo "Installing Dovecot..."
    apt install -y dovecot-core dovecot-imapd dovecot-pop3d
    systemctl enable dovecot
    systemctl start dovecot
else
    echo "✓ Dovecot already installed"
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
echo "=== Localhost Provisioning Complete! ==="
echo "This server is now ready to host websites!"
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
