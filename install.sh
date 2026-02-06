#!/bin/bash

# RPanel Flexible Installer
# Usage: DEPLOY_MODE=[fresh|bench|dependency] ./install.sh
# Default mode is "fresh" (full VPS install).

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0;0m'

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}       RPanel Flexible Installer               ${NC}"
echo -e "${BLUE}=================================================${NC}"

# Determine deployment mode
MODE="${DEPLOY_MODE:-fresh}"
if [[ "$MODE" != "fresh" && "$MODE" != "bench" ]]; then
  echo -e "${RED}Invalid DEPLOY_MODE: $MODE. Use 'fresh' or 'bench'.${NC}"
  echo ""
  echo "Modes:"
  echo "  fresh - Full VPS setup (system packages, MariaDB, Bench, RPanel)"
  echo "  bench - Add RPanel to existing Frappe bench"
  echo ""
  exit 1
fi

echo -e "${GREEN}Deploy mode: $MODE${NC}"

# Non-interactive mode for CI
if [[ "$CI" == "true" || "$NON_INTERACTIVE" == "true" ]]; then
  echo -e "${GREEN}CI environment detected. Using automated defaults.${NC}"
  DOMAIN_NAME=${DOMAIN_NAME:-rpanel.local}
  SELF_HOSTED=${SELF_HOSTED:-Y}
  SKIP_SSL=true
else
  # Prompt for domain in fresh mode
  if [[ "$MODE" == "fresh" ]]; then
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}Domain Configuration${NC}"
    echo -e "${BLUE}=================================================${NC}"
    echo ""
    read -p "Enter your domain name (or press Enter for rpanel.local): " DOMAIN_NAME
    DOMAIN_NAME=${DOMAIN_NAME:-rpanel.local}
    echo -e "${GREEN}Using domain: $DOMAIN_NAME${NC}"
    echo ""
    
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}Hosting Mode${NC}"
    echo -e "${BLUE}=================================================${NC}"
    echo ""
    echo "Will this server also host websites?"
    echo "  Yes - Install hosting services (PHP, Nginx, email, etc.) on this server"
    echo "  No  - Use this as a control panel only (manage remote servers)"
    echo ""
    read -p "Host websites on this server? (Y/n): " SELF_HOSTED
    SELF_HOSTED=${SELF_HOSTED:-Y}
    echo ""
  fi
fi

# Helper to install system packages (only for fresh mode)
install_system_deps() {
  echo -e "${GREEN}Installing system packages...${NC}"
  apt-get update && apt-get upgrade -y
  
  # Core dependencies for Frappe/RPanel
  apt-get install -y git python3-dev python3-pip python3-venv redis-server software-properties-common mariadb-server mariadb-client xvfb libfontconfig wkhtmltopdf curl
  
  # Email services (needed for RPanel control panel to send notifications)
  echo -e "${GREEN}Installing email services...${NC}"
  apt-get install -y exim4 exim4-daemon-heavy opendkim opendkim-tools
  
  # Configure Exim4 for internet mail
  debconf-set-selections <<EOF
exim4-config exim4/dc_eximconfig_configtype select internet site; mail is sent and received directly using SMTP
exim4-config exim4/dc_other_hostnames string
exim4-config exim4/dc_local_interfaces string 127.0.0.1 ; ::1
EOF
  dpkg-reconfigure -f noninteractive exim4-config
  systemctl enable exim4
  systemctl start exim4
  
  # SSL/TLS (for securing the control panel domain)
  apt-get install -y certbot python3-certbot-nginx
  
  # Node.js (required by Frappe)
  curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
  apt-get install -y nodejs
  
  # Install Yarn
  npm install -g yarn
  
  # Configure automatic security updates
  echo -e "${GREEN}Configuring automatic security updates...${NC}"
  cat > /etc/apt/apt.conf.d/50unattended-upgrades <<EOF
Unattended-Upgrade::Allowed-Origins {
    "\${distro_id}:\${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF
  
  cat > /etc/apt/apt.conf.d/20auto-upgrades <<EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
  
  systemctl enable unattended-upgrades
  systemctl start unattended-upgrades
  echo -e "${GREEN}✓ Automatic security updates enabled${NC}"
}

# Helper to configure MariaDB (only for fresh mode)
configure_mariadb() {
  echo -e "${GREEN}Configuring MariaDB...${NC}"
  
  # Generate random secure password
  DB_ROOT_PASS=$(openssl rand -base64 32)
  
  # Secure MariaDB installation
  mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$DB_ROOT_PASS'; FLUSH PRIVILEGES;" || true
  mysql -e "DELETE FROM mysql.user WHERE User='';" || true
  mysql -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');" || true
  mysql -e "DROP DATABASE IF EXISTS test;" || true
  mysql -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';" || true
  mysql -e "FLUSH PRIVILEGES;" || true
  
  # Save password securely
  cat > /root/.my.cnf <<EOF
[client]
user=root
password=$DB_ROOT_PASS
EOF
  chmod 600 /root/.my.cnf
  
  # Configure MariaDB for Frappe
  cat > /etc/mysql/mariadb.conf.d/frappe.cnf <<EOF
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
max_allowed_packet = 256M
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_file_per_table = 1
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# Security hardening
bind-address = 127.0.0.1
skip-networking = 0
local-infile = 0
EOF
  systemctl restart mariadb
}

# Helper to create frappe system user (only for fresh mode)
create_frappe_user() {
  echo -e "${GREEN}Creating frappe system user...${NC}"
  if ! id -u frappe > /dev/null 2>&1; then
    useradd -m -s /bin/bash frappe
    usermod -aG sudo frappe
    echo "frappe ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
  fi
}

# Helper to install Bench (fresh or bench mode)
install_bench() {
  echo -e "${GREEN}Installing Bench...${NC}"
  sudo -u frappe -H bash <<EOF
cd /home/frappe
if [ ! -d "frappe-bench" ]; then
  pip3 install frappe-bench
  bench init frappe-bench --frappe-branch version-15
fi
EOF
}

# Helper to fetch latest RPanel release tag
fetch_latest_tag() {
  python3 /home/frappe/frappe-bench/apps/rpanel/scripts/get_latest_release.py 2>/dev/null || echo ""
}

# Main logic per mode
case "$MODE" in
  fresh)
    install_system_deps
    configure_mariadb
    create_frappe_user
    install_bench
    ;;
  bench)
    # Existing bench - just ensure frappe user exists
    create_frappe_user || true
    ;;
esac

# Install/Update RPanel app
LATEST_TAG=$(fetch_latest_tag)
if [ -z "$LATEST_TAG" ]; then
  TAG_OPTION=""
else
  TAG_OPTION="--branch $LATEST_TAG"
fi

sudo -u frappe -H bash <<EOF
cd /home/frappe/frappe-bench
if [ ! -d "apps/rpanel" ]; then
  bench get-app https://github.com/RokctAI/rpanel.git $TAG_OPTION
else
  cd apps/rpanel
  git fetch --tags
  if [ -n "$TAG_OPTION" ]; then
    git checkout $LATEST_TAG
  fi
  cd ../..
fi

# Ensure site exists
SITE_NAME="${DOMAIN_NAME:-rpanel.local}"
if [ ! -d "sites/$SITE_NAME" ]; then
  bench new-site $SITE_NAME --admin-password admin --db-root-password $DB_ROOT_PASS --install-app rpanel || true
fi
bench --site $SITE_NAME install-app rpanel
EOF

# Production setup
echo -e "${GREEN}Configuring production services...${NC}"
sudo bench setup production frappe

# Provision localhost if self-hosted mode
if [[ "$MODE" == "fresh" && ("$SELF_HOSTED" == "Y" || "$SELF_HOSTED" == "y") ]]; then
  echo -e "${GREEN}=================================================${NC}"
  echo -e "${GREEN}Provisioning localhost for website hosting...${NC}"
  echo -e "${GREEN}=================================================${NC}"
  echo ""
  
  # Run the provisioning script
  bash /home/frappe/frappe-bench/apps/rpanel/scripts/provision_localhost.sh
  
  echo -e "${GREEN}Localhost provisioning complete!${NC}"
fi

# Setup SSL if domain is not localhost/rpanel.local
if [[ "$MODE" == "fresh" && "$DOMAIN_NAME" != "rpanel.local" && "$DOMAIN_NAME" != "localhost" && "$SKIP_SSL" != "true" ]]; then
  echo -e "${GREEN}Setting up SSL for $DOMAIN_NAME...${NC}"
  echo -e "${BLUE}Note: Make sure $DOMAIN_NAME points to this server's IP address${NC}"
  read -p "Press Enter to continue with SSL setup (or Ctrl+C to skip)..."
  
  # Run certbot for the domain
  certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --register-unsafely-without-email || {
    echo -e "${RED}SSL setup failed. You can run 'sudo certbot --nginx -d $DOMAIN_NAME' manually later.${NC}"
  }
fi

# Final output
echo -e "${GREEN}Installation complete!${NC}"
SITE_NAME="${DOMAIN_NAME:-rpanel.local}"
if [[ "$DOMAIN_NAME" != "rpanel.local" && "$DOMAIN_NAME" != "localhost" ]]; then
  echo -e "${BLUE}URL: https://$DOMAIN_NAME${NC}"
else
  echo -e "${BLUE}URL: http://$(curl -s ifconfig.me)${NC}"
fi
echo -e "${BLUE}Site: $SITE_NAME${NC}"
echo -e "${BLUE}Admin Password: admin${NC}"
echo ""
echo -e "${GREEN}Email service (Exim4) is configured and running.${NC}"
echo -e "${GREEN}RPanel can now send email notifications.${NC}"


# RPanel Standalone Installer
# Installs system dependencies, Frappe Bench, and RPanel on a fresh server.
# Supported OS: Ubuntu 22.04 LTS, Debian 11/12

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0;m'

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}       RPanel Standalone Installer               ${NC}"
echo -e "${BLUE}=================================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# 1. System Updates & Dependencies
echo -e "${GREEN}Step 1/6: Updating system and installing dependencies...${NC}"
apt-get update && apt-get upgrade -y
apt-get install -y git python3-dev python3-pip python3-venv redis-server software-properties-common mariadb-server mariadb-client xvfb libfontconfig wkhtmltopdf curl

# Install Node.js 24
curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
apt-get install -y nodejs

# Install Yarn
npm install -g yarn

# 2. Configure MariaDB
echo -e "${GREEN}Step 2/6: Configuring Database...${NC}"
DB_ROOT_PASS="rpanel_secure_db_pass"
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$DB_ROOT_PASS'; FLUSH PRIVILEGES;" || true
cat > /etc/mysql/mariadb.conf.d/frappe.cnf <<EOF
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[mysql]
default-character-set = utf8mb4
EOF
systemctl restart mariadb

# 3. Create Frappe User
echo -e "${GREEN}Step 3/6: Creating 'frappe' user...${NC}"
if ! id -u frappe > /dev/null 2>&1; then
    useradd -m -s /bin/bash frappe
    usermod -aG sudo frappe
    echo "frappe ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
    # 4. Install Bench (as frappe user) - moved here
    echo -e "${GREEN}Step 4/6: Installing Frappe Bench...${NC}"
    sudo -u frappe -H bash <<EOF
cd /home/frappe
if [ ! -d "frappe-bench" ]; then
    pip3 install frappe-bench
    bench init frappe-bench --frappe-branch version-15
fi
EOF
fi

# 5. Install RPanel (fetch latest release tag)
echo -e "${GREEN}Step 5/6: Installing RPanel...${NC}"
# Determine latest release tag via helper script
LATEST_TAG=$(python3 /home/frappe/frappe-bench/apps/rpanel/scripts/get_latest_release.py 2>/dev/null || echo "")
if [ -z "$LATEST_TAG" ]; then
    echo -e "${RED}Could not determine latest release – falling back to cloning main branch${NC}"
    TAG_OPTION=""
else
    echo -e "${BLUE}Installing RPanel $LATEST_TAG${NC}"
    TAG_OPTION="--branch $LATEST_TAG"
fi

sudo -u frappe -H bash <<EOF
cd /home/frappe/frappe-bench
# Get RPanel app if not exists
if [ ! -d "apps/rpanel" ]; then
    bench get-app https://github.com/RokctAI/rpanel.git $TAG_OPTION
else
    cd apps/rpanel
    git fetch --tags
    if [ -n "$TAG_OPTION" ]; then
        git checkout $LATEST_TAG
    fi
    cd ../..
fi
# Create site if not exists
if [ ! -d "sites/rpanel.local" ]; then
    bench new-site rpanel.local --admin-password admin --db-root-password $DB_ROOT_PASS --install-app rpanel || true
fi
# Install RPanel on site
bench --site rpanel.local install-app rpanel
EOF

# 5.5 Setup production (only for production installs)
echo -e "${GREEN}Step 5.5/6: Configuring production services...${NC}"
sudo bench setup production frappe


# 6. Finalize
echo -e "${GREEN}Step 6/6: Finalizing setup...${NC}"
echo -e "${BLUE}=================================================${NC}"
echo -e "${GREEN}RPanel installation complete!${NC}"
echo -e "${BLUE}URL: http://$(curl -s ifconfig.me)${NC}"
echo -e "${BLUE}Admin Password: admin${NC}"
echo -e "${BLUE}=================================================${NC}"
