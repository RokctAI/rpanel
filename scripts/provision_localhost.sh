#!/bin/bash
# RPanel Localhost Provisioning Script
# Extracted from server_provisioner.py for self-hosted installations

set -e

INSTALL_LOG="/tmp/rpanel_install.log"
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0;0m'

# Helper: run a command quietly with status output
run_prov() {
  local label="$1"
  shift
  echo -n -e "${BLUE}  - ${label}... ${NC}"
  if "$@" >>"$INSTALL_LOG" 2>&1; then
    echo -e "${GREEN}✓ DONE${NC}"
  else
    echo -e "${RED}✗ FAILED${NC}"
    echo -e "${RED}Check $INSTALL_LOG for details.${NC}"
    exit 1
  fi
}

# Helper for services to handle Docker/systemd
safe_service() {
  local action="$1"
  local service="$2"
  if [ -d /run/systemd/system ]; then
    systemctl "$action" "$service" >>"$INSTALL_LOG" 2>&1 || true
  else
    service "$service" "$action" >>"$INSTALL_LOG" 2>&1 || true
  fi
}

APT_QUIET=(-y -o=Dpkg::Use-Pty=0)

echo "=== RPanel Localhost Provisioning ==="
echo "Installing hosting services on this server..."

# Detect OS
if [ -f /etc/os-release ]; then
  . /etc/os-release
  DISTRO=$ID
  CODENAME=$VERSION_CODENAME
else
  echo -e "${RED}Unsupported OS: /etc/os-release not found.${NC}"
  exit 1
fi

# Fallback for Debian Trixie (testing) if codename is empty
if [[ "$DISTRO" == "debian" && -z "$CODENAME" ]]; then
  CODENAME="trixie"
fi

# Update system
echo -e "${BLUE}[1/12] Updating system packages...${NC}"
run_prov "Updating package lists" apt-get update
run_prov "Installing basic tools" apt-get install "${APT_QUIET[@]}" curl ca-certificates gnupg build-essential pkg-config git
mkdir -p /etc/apt/keyrings

# Repository Setup
echo -e "${BLUE}[2/12] Setting up repositories...${NC}"
# PHP PPA/Repo
if [[ "$DISTRO" == "ubuntu" ]]; then
  run_prov "Adding PHP PPA" add-apt-repository -y ppa:ondrej/php
else
  run_prov "Adding Sury PHP Repo" bash -c "curl -fsSL https://packages.sury.org/php/apt.gpg | gpg --dearmor --batch --yes -o /etc/apt/keyrings/sury-php.gpg && \
        echo \"deb [signed-by=/etc/apt/keyrings/sury-php.gpg] https://packages.sury.org/php/ $CODENAME main\" > /etc/apt/sources.list.d/sury-php.list"
fi

# PostgreSQL PGDG Repo
run_prov "Adding PostgreSQL Repo" bash -c "curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor --batch --yes -o /etc/apt/keyrings/postgresql.gpg && \
    echo \"deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $CODENAME-pgdg main\" > /etc/apt/sources.list.d/pgdg.list"

# Node.js 24 Repo (Modern Setup)
run_prov "Adding NodeSource GPG key" bash -c "curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor --batch --yes -o /etc/apt/keyrings/nodesource.gpg"
run_prov "Adding NodeSource Repo" bash -c "echo \"deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main\" > /etc/apt/sources.list.d/nodesource.list"

run_prov "Updating package lists after repo additions" apt-get update

# Install Nginx
echo -e "${BLUE}[3/12] Installing Nginx...${NC}"
run_prov "Installing Nginx" apt-get install "${APT_QUIET[@]}" nginx
safe_service enable nginx
safe_service start nginx

# Install PostgreSQL 16
echo -e "${BLUE}[4/12] Installing PostgreSQL 16...${NC}"
run_prov "Installing PostgreSQL" apt-get install "${APT_QUIET[@]}" postgresql-16 postgresql-client-16 postgresql-contrib-16 postgresql-16-pgvector libpq-dev
safe_service enable postgresql
safe_service start postgresql

# Install PHP versions
echo -e "${BLUE}[5/12] Installing PHP versions...${NC}"
run_prov "Installing PHP 8.3" apt-get install "${APT_QUIET[@]}" php8.3-fpm php8.3-mysql php8.3-pgsql php8.3-curl php8.3-gd php8.3-mbstring php8.3-xml php8.3-zip
run_prov "Installing PHP 8.2" apt-get install "${APT_QUIET[@]}" php8.2-fpm php8.2-mysql php8.2-pgsql php8.2-curl php8.2-gd php8.2-mbstring php8.2-xml php8.2-zip
run_prov "Installing PHP 8.1" apt-get install "${APT_QUIET[@]}" php8.1-fpm php8.1-mysql php8.1-pgsql php8.1-curl php8.1-gd php8.1-mbstring php8.1-xml php8.1-zip

# Install Node.js & Tools
echo -e "${BLUE}[6/12] Installing Node.js & global tools...${NC}"
run_prov "Installing Node.js" apt-get install "${APT_QUIET[@]}" nodejs
run_prov "Installing Yarn" npm install -g yarn

# Install Dovecot
echo -e "${BLUE}[7/12] Installing Dovecot...${NC}"
run_prov "Installing Dovecot" apt-get install "${APT_QUIET[@]}" dovecot-core dovecot-imapd dovecot-pop3d
safe_service enable dovecot
safe_service start dovecot

# Install Roundcube
echo -e "${BLUE}[8/12] Installing Roundcube...${NC}"
run_prov "Installing Roundcube" env DEBIAN_FRONTEND=noninteractive apt-get install "${APT_QUIET[@]}" roundcube roundcube-core roundcube-mysql roundcube-plugins

# Install phpMyAdmin
echo -e "${BLUE}[9/12] Installing phpMyAdmin...${NC}"
run_prov "Installing phpMyAdmin" env DEBIAN_FRONTEND=noninteractive apt-get install "${APT_QUIET[@]}" phpmyadmin

# Install WP-CLI
echo -e "${BLUE}[10/12] Installing WP-CLI...${NC}"
if ! command -v wp &>/dev/null; then
  run_prov "Downloading WP-CLI" curl -sO https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
  chmod +x wp-cli.phar
  mv wp-cli.phar /usr/local/bin/wp
else
  echo -e "  ${GREEN}✓ WP-CLI already installed${NC}"
fi

# Install Security Tools
echo -e "${BLUE}[11/12] Installing security tools...${NC}"
run_prov "Installing ClamAV" apt-get install "${APT_QUIET[@]}" clamav clamav-daemon
systemctl stop clamav-freshclam >>"$INSTALL_LOG" 2>&1 || true
run_prov "Updating ClamAV" freshclam # Can be slow/fail in CI
safe_service start clamav-freshclam
safe_service enable clamav-daemon
safe_service start clamav-daemon

run_prov "Installing Fail2Ban" apt-get install "${APT_QUIET[@]}" fail2ban
safe_service enable fail2ban
safe_service start fail2ban

# Install UFW
echo -e "${BLUE}[12/12] Installing/Configuring UFW...${NC}"
run_prov "Installing UFW" apt-get install "${APT_QUIET[@]}" ufw
ufw default deny incoming >>"$INSTALL_LOG" 2>&1 || true
ufw default allow outgoing >>"$INSTALL_LOG" 2>&1 || true
ufw allow ssh >>"$INSTALL_LOG" 2>&1 || true
ufw allow http >>"$INSTALL_LOG" 2>&1 || true
ufw allow https >>"$INSTALL_LOG" 2>&1 || true

# Create directory structure
echo -n -e "${BLUE}  - Setting up directory structure... ${NC}"
mkdir -p /var/www
mkdir -p /var/backups/websites
mkdir -p /var/lib/rokct/hosting/cache
chown -R www-data:www-data /var/www
chmod 755 /var/www
echo -e "${GREEN}✓ DONE${NC}"

echo ""
echo -e "${GREEN}=== Localhost Provisioning Complete! ===${NC}"
