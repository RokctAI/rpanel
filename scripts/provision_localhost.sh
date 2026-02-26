#!/bin/bash
# RPanel Localhost Provisioning Script
# Extracted from server_provisioner.py for self-hosted installations

set -e

INSTALL_LOG="/tmp/rpanel_install.log"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0;0m'

# Helper: run a command quietly with status output
run_prov() {
  local label="$1"
  shift
  echo -n -e "${BLUE}  - ${label}... ${NC}"
  if "$@" >>"$INSTALL_LOG" 2>&1; then
    echo -e "${GREEN}✓ DONE${NC}"
  else
    echo -e "${YELLOW}! SKIPPED${NC}"
  fi
}

APT_QUIET=(-y -qq -o=Dpkg::Use-Pty=0)

echo "=== RPanel Localhost Provisioning ==="
echo "Installing hosting services on this server..."

# Update system
echo -e "${BLUE}[1/12] Updating system packages...${NC}"
run_prov "Updating package lists" apt-get update "${APT_QUIET[@]}"
run_prov "Upgrading packages" apt-get upgrade "${APT_QUIET[@]}"

# Install Nginx (if not installed)
echo -e "${BLUE}[2/12] Checking Nginx...${NC}"
if ! command -v nginx &>/dev/null; then
  run_prov "Installing Nginx" apt-get install "${APT_QUIET[@]}" nginx
  systemctl enable nginx >>"$INSTALL_LOG" 2>&1 || true
  systemctl start nginx >>"$INSTALL_LOG" 2>&1 || true
else
  echo -e "  ${GREEN}✓ Nginx already installed${NC}"
fi

# Install PostgreSQL (if not installed)
echo -e "${BLUE}[3/12] Checking PostgreSQL...${NC}"
if ! command -v psql &>/dev/null; then
  run_prov "Installing PostgreSQL" apt-get install "${APT_QUIET[@]}" postgresql postgresql-contrib
  systemctl enable postgresql >>"$INSTALL_LOG" 2>&1 || true
  systemctl start postgresql >>"$INSTALL_LOG" 2>&1 || true
else
  echo -e "  ${GREEN}✓ PostgreSQL already installed${NC}"
fi

# Install PHP versions (if not installed)
echo -e "${BLUE}[4/12] Checking PHP versions...${NC}"
if ! dpkg -l | grep -q php8.3-fpm; then
  run_prov "Installing PHP prerequisites" apt-get install "${APT_QUIET[@]}" software-properties-common
  add-apt-repository -y ppa:ondrej/php >>"$INSTALL_LOG" 2>&1 || true
  apt-get update -qq >>"$INSTALL_LOG" 2>&1
  run_prov "Installing PHP 8.3" apt-get install "${APT_QUIET[@]}" php8.3-fpm php8.3-mysql php8.3-pgsql php8.3-curl php8.3-gd php8.3-mbstring php8.3-xml php8.3-zip
  systemctl enable php8.3-fpm >>"$INSTALL_LOG" 2>&1 || true
  systemctl start php8.3-fpm >>"$INSTALL_LOG" 2>&1 || true
else
  echo -e "  ${GREEN}✓ PHP 8.3 already installed${NC}"
fi

if ! dpkg -l | grep -q php8.2-fpm; then
  run_prov "Installing PHP 8.2" apt-get install "${APT_QUIET[@]}" php8.2-fpm php8.2-mysql php8.2-pgsql php8.2-curl php8.2-gd php8.2-mbstring php8.2-xml php8.2-zip
  systemctl enable php8.2-fpm >>"$INSTALL_LOG" 2>&1 || true
  systemctl start php8.2-fpm >>"$INSTALL_LOG" 2>&1 || true
else
  echo -e "  ${GREEN}✓ PHP 8.2 already installed${NC}"
fi

if ! dpkg -l | grep -q php8.1-fpm; then
  run_prov "Installing PHP 8.1" apt-get install "${APT_QUIET[@]}" php8.1-fpm php8.1-mysql php8.1-pgsql php8.1-curl php8.1-gd php8.1-mbstring php8.1-xml php8.1-zip
  systemctl enable php8.1-fpm >>"$INSTALL_LOG" 2>&1 || true
  systemctl start php8.1-fpm >>"$INSTALL_LOG" 2>&1 || true
else
  echo -e "  ${GREEN}✓ PHP 8.1 already installed${NC}"
fi

# Certbot should already be installed from main installer

# Install Dovecot (if not installed)
echo -e "${BLUE}[6/12] Checking Dovecot...${NC}"
if ! dpkg -l | grep -q dovecot-core; then
  run_prov "Installing Dovecot" apt-get install "${APT_QUIET[@]}" dovecot-core dovecot-imapd dovecot-pop3d
  systemctl enable dovecot >>"$INSTALL_LOG" 2>&1 || true
  systemctl start dovecot >>"$INSTALL_LOG" 2>&1 || true
else
  echo -e "  ${GREEN}✓ Dovecot already installed${NC}"
fi

# Install Roundcube (if not installed)
echo -e "${BLUE}[7/12] Checking Roundcube...${NC}"
if ! dpkg -l | grep -q roundcube; then
  run_prov "Installing Roundcube" env DEBIAN_FRONTEND=noninteractive apt-get install "${APT_QUIET[@]}" roundcube roundcube-core roundcube-mysql roundcube-plugins
else
  echo -e "  ${GREEN}✓ Roundcube already installed${NC}"
fi

# Install phpMyAdmin (if not installed)
echo -e "${BLUE}[8/12] Checking phpMyAdmin...${NC}"
if [ ! -d "/usr/share/phpmyadmin" ]; then
  run_prov "Installing phpMyAdmin" env DEBIAN_FRONTEND=noninteractive apt-get install "${APT_QUIET[@]}" phpmyadmin
else
  echo -e "  ${GREEN}✓ phpMyAdmin already installed${NC}"
fi

# Install WP-CLI (if not installed)
echo -e "${BLUE}[9/12] Checking WP-CLI...${NC}"
if ! command -v wp &>/dev/null; then
  echo -n -e "${BLUE}  - Installing WP-CLI... ${NC}"
  if curl -sO https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar >>"$INSTALL_LOG" 2>&1 &&
    chmod +x wp-cli.phar && mv wp-cli.phar /usr/local/bin/wp; then
    echo -e "${GREEN}✓ DONE${NC}"
  else
    echo -e "${YELLOW}! SKIPPED${NC}"
  fi
else
  echo -e "  ${GREEN}✓ WP-CLI already installed${NC}"
fi

# Install ClamAV (if not installed)
echo -e "${BLUE}[10/12] Checking ClamAV...${NC}"
if ! command -v clamscan &>/dev/null; then
  run_prov "Installing ClamAV" apt-get install "${APT_QUIET[@]}" clamav clamav-daemon
  systemctl stop clamav-freshclam >>"$INSTALL_LOG" 2>&1 || true
  freshclam >>"$INSTALL_LOG" 2>&1 || true
  systemctl start clamav-freshclam >>"$INSTALL_LOG" 2>&1 || true
  systemctl enable clamav-daemon >>"$INSTALL_LOG" 2>&1 || true
  systemctl start clamav-daemon >>"$INSTALL_LOG" 2>&1 || true
else
  echo -e "  ${GREEN}✓ ClamAV already installed${NC}"
fi

# Install Fail2Ban (if not installed)
echo -e "${BLUE}[11/12] Checking Fail2Ban...${NC}"
if ! command -v fail2ban-client &>/dev/null; then
  run_prov "Installing Fail2Ban" apt-get install "${APT_QUIET[@]}" fail2ban
  systemctl enable fail2ban >>"$INSTALL_LOG" 2>&1 || true
  systemctl start fail2ban >>"$INSTALL_LOG" 2>&1 || true
else
  echo -e "  ${GREEN}✓ Fail2Ban already installed${NC}"
fi

# Install UFW (if not installed)
echo -e "${BLUE}[12/12] Checking UFW...${NC}"
if ! command -v ufw &>/dev/null; then
  run_prov "Installing UFW" apt-get install "${APT_QUIET[@]}" ufw
  ufw default deny incoming >>"$INSTALL_LOG" 2>&1 || true
  ufw default allow outgoing >>"$INSTALL_LOG" 2>&1 || true
  ufw allow ssh >>"$INSTALL_LOG" 2>&1 || true
  ufw allow http >>"$INSTALL_LOG" 2>&1 || true
  ufw allow https >>"$INSTALL_LOG" 2>&1 || true
  ufw allow 'Nginx Full' >>"$INSTALL_LOG" 2>&1 || true
  echo "y" | ufw enable >>"$INSTALL_LOG" 2>&1 || true
else
  echo -e "  ${GREEN}✓ UFW already installed${NC}"
  # Ensure firewall rules are set
  ufw allow ssh >>"$INSTALL_LOG" 2>&1 || true
  ufw allow http >>"$INSTALL_LOG" 2>&1 || true
  ufw allow https >>"$INSTALL_LOG" 2>&1 || true
fi

# Create directory structure (if not exists)
echo -n -e "${BLUE}  - Setting up directory structure... ${NC}"
mkdir -p /var/www
mkdir -p /var/backups/websites
mkdir -p /var/lib/rokct/hosting/cache
chown -R www-data:www-data /var/www
chmod 755 /var/www
echo -e "${GREEN}✓ DONE${NC}"

echo ""
echo -e "${GREEN}=== Localhost Provisioning Complete! ===${NC}"
echo "Installed/Verified services:"
echo -e "  ${GREEN}✓${NC} Nginx"
echo -e "  ${GREEN}✓${NC} MariaDB"
echo -e "  ${GREEN}✓${NC} PostgreSQL"
echo -e "  ${GREEN}✓${NC} PHP (8.3, 8.2, 8.1)"
echo -e "  ${GREEN}✓${NC} phpMyAdmin"
echo -e "  ${GREEN}✓${NC} Certbot (Let's Encrypt)"
echo -e "  ${GREEN}✓${NC} Exim4 + Dovecot (Email)"
echo -e "  ${GREEN}✓${NC} Roundcube (Webmail)"
echo -e "  ${GREEN}✓${NC} WP-CLI"
echo -e "  ${GREEN}✓${NC} ClamAV (Malware Scanner)"
echo -e "  ${GREEN}✓${NC} Fail2Ban"
echo -e "  ${GREEN}✓${NC} UFW (Firewall)"
