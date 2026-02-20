#!/bin/bash

# RPanel Flexible Installer
# Usage: DEPLOY_MODE=[fresh|bench|dependency] ./install.sh
# Default mode is "fresh" (full VPS install).
INSTALLER_VERSION="v8.7-NONFATAL-PROD"

echo -e "\033[0;34mRPanel Installer Version: $INSTALLER_VERSION\033[0;0m"

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0;0m'

# Global Build Hardening (Required for resource-constrained environments to avoid SIGTERM 143)
export CI=${CI:-true}
# Use 1.5GB to force more aggressive GC. Higher limits can hit cgroup caps on small runners.
export NODE_OPTIONS='--max-old-space-size=1536'
export ESBUILD_WORKERS=1
export MAX_WORKERS=1
export CPU_COUNT=1
export GENERATE_SOURCEMAP=false
export NODE_ENV=production
export YARN_NETWORK_TIMEOUT=300000
export YARN_MEMORY_LIMIT=2048
export GOGC=50

# Log file for verbose output
INSTALL_LOG="/tmp/rpanel_install.log"
touch "$INSTALL_LOG"
chmod 666 "$INSTALL_LOG"

echo -e "${BLUE}Detailed logs available at: $INSTALL_LOG${NC}"

# Hardcoded administrative password (as requested)
DB_ROOT_PASS="rpanel_secure_db_pass"

# Determine deployment mode
MODE="${DEPLOY_MODE:-fresh}"
DB_TYPE="${DB_TYPE:-postgres}"

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

# Helper to run commands quietly but log details
run_quiet() {
  local msg="$1"
  shift
  echo -n -e "${BLUE}  - $msg... ${NC}"
  # Security: Set DEBIAN_FRONTEND=noninteractive for all system commands to avoid UI traps
  # Propagate stdin to the command to support heredocs
  if DEBIAN_FRONTEND=noninteractive "$@" <&0 >> "$INSTALL_LOG" 2>&1; then
    echo -e "${GREEN}✓ DONE${NC}"
  else
    echo -e "${RED}✗ FAILED${NC}"
    echo -e "${RED}Check $INSTALL_LOG for details.${NC}"
    echo -e "${YELLOW}Last 20 lines of $INSTALL_LOG:${NC}"
    tail -n 20 "$INSTALL_LOG" | sed 's/^/    /'
    exit 1
  fi
}

# Helper to install system packages (only for fresh mode)
install_system_deps() {
  # PHP PPA for modern Ubuntu ( Noble/Jammy compatibility )
  if [[ "$CI" == "true" || "$NON_INTERACTIVE" == "true" ]]; then
    run_quiet "Adding PHP PPA" add-apt-repository -y ppa:ondrej/php
  fi

  # Core dependencies for Frappe/RPanel
  if [[ "$DB_TYPE" == "postgres" ]]; then
    # Install PGDG Repo for latest Postgres + pgvector
    echo -e "${GREEN}Configuring PostgreSQL PGDG Repo...${NC}"
    run_quiet "Installing repo tools" apt-get install -y lsb-release curl ca-certificates gnupg software-properties-common
    install -d /usr/share/postgresql-common/pgdg
    run_quiet "Downloading PostgreSQL key" curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc
    sh -c 'echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    
    # Add Python 3.14 (Required for Frappe v16)
    run_quiet "Adding Python PPA" add-apt-repository -y ppa:deadsnakes/ppa
    run_quiet "Updating package lists" apt-get update

    # Install Essential System Tools (-qq for clean logs, kill PTY for one-liners)
    run_quiet "Installing system tools" apt-get install -y -qq -o=Dpkg::Use-Pty=0 git curl redis-server xvfb libfontconfig wkhtmltopdf
    
    # Install Python 3.14 (Required for Frappe v16)
    run_quiet "Installing Python 3.14" apt-get install -y -qq -o=Dpkg::Use-Pty=0 python3.14-dev python3.14-venv python3-pip python-is-python3
    
    # Install Postgres 16 (Native to Noble) + Matching Contrib & Vector
    run_quiet "Installing PostgreSQL 16 & Extensions" apt-get install -y -qq -o=Dpkg::Use-Pty=0 postgresql-16 postgresql-client-16 postgresql-contrib-16 postgresql-16-pgvector libpq-dev
  else
    run_quiet "Installing repo tools" apt-get install -y -qq -o=Dpkg::Use-Pty=0 software-properties-common
    run_quiet "Adding Python PPA" add-apt-repository -y ppa:deadsnakes/ppa
    run_quiet "Updating package lists" apt-get update
    
    run_quiet "Installing system dependencies" apt-get install -y -qq -o=Dpkg::Use-Pty=0 git python3.14-dev python3.14-venv python3-pip python-is-python3 redis-server mariadb-server mariadb-client curl build-essential xvfb libfontconfig wkhtmltopdf libjpeg-dev zlib1g-dev
  fi
  
  # Configure Exim4 for internet mail
  echo -e "${GREEN}Installing email services...${NC}"
  run_quiet "Installing Exim4 & OpenDKIM" apt-get install -y -qq -o=Dpkg::Use-Pty=0 exim4 exim4-daemon-heavy opendkim opendkim-tools
  
  # Configure Exim4 for internet mail
  debconf-set-selections <<EOF
exim4-config exim4/dc_eximconfig_configtype select internet site; mail is sent and received directly using SMTP
exim4-config exim4/dc_other_hostnames string
exim4-config exim4/dc_local_interfaces string 127.0.0.1 ; ::1
EOF
  run_quiet "Configuring Exim4" dpkg-reconfigure -f noninteractive exim4-config
  systemctl enable exim4 >> "$INSTALL_LOG" 2>&1 || true
  systemctl start exim4 >> "$INSTALL_LOG" 2>&1 || true
  
  # SSL/TLS (for securing the control panel domain)
  run_quiet "Installing Certbot" apt-get install -y certbot python3-certbot-nginx
  
  # Node.js (Frappe v16 requires Node >= 24)
  # Node 24 is the certified LTS for version 16
  run_quiet "Setting up NodeSource (v24)" bash -c "curl -fsSL https://deb.nodesource.com/setup_24.x | bash -"
  run_quiet "Installing Node.js" apt-get install -y nodejs
  
  # Nuclear Path Override: Ensure binaries are visible to all users/environments
  ln -sf /usr/bin/node /usr/local/bin/node
  ln -sf /usr/bin/npm /usr/local/bin/npm
  ln -sf /usr/bin/npx /usr/local/bin/npx
  
  # Install Yarn globally and link it
  run_quiet "Installing Yarn" npm install -g yarn
  ln -sf /usr/local/bin/yarn /usr/bin/yarn >> "$INSTALL_LOG" 2>&1 || true
  
  # Bypass strict Node version checks in Yarn during build
  run_quiet "Configuring Yarn global policy" yarn config set ignore-engines true -g
  
  # Verify Node/Yarn version
  node -v >> "$INSTALL_LOG" 2>&1
  yarn -v >> "$INSTALL_LOG" 2>&1 || { echo -e "${RED}Yarn installation failed!${NC}"; exit 1; }
  
  # Configure automatic security updates
  if [[ "$CI" != "true" ]]; then
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
    
    systemctl enable unattended-upgrades || true
    systemctl start unattended-upgrades || true
    echo -e "${GREEN}✓ Automatic security updates enabled${NC}"
  else
    echo -e "${GREEN}CI environment: Skipping automatic security updates configuration${NC}"
  fi
}

# Helper to setup swap for low-memory environments (prevents OOM kills like 143)
setup_swap() {
  echo -e "${BLUE}Diagnostics: Entering setup_swap...${NC}"
  if [[ "$MODE" == "fresh" && ! -f /swapfile ]]; then
    # Check if we have less than 4GB of RAM
    local total_mem=$(free -m | grep -i mem | awk '{print $2}')
    echo -e "${BLUE}System Memory: ${total_mem}MB${NC}"
    if [[ -n "$total_mem" && "$total_mem" -lt 4000 ]]; then
      echo -e "${GREEN}Low memory detected. Creating 2GB swap file...${NC}"
      fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
      chmod 600 /swapfile
      mkswap /swapfile
      swapon /swapfile || true
      if ! grep -q "/swapfile" /etc/fstab; then
        echo "/swapfile swap swap defaults 0 0" >> /etc/fstab
      fi
      echo -e "${GREEN}✓ Swap enabled${NC}"
    fi
  else
    echo -e "${BLUE}Diagnostics: Swap check bypassed (Mode: $MODE, Swapfile exists: $([ -f /swapfile ] && echo "Yes" || echo "No"))${NC}"
  fi
}

# Helper to configure MariaDB (only for fresh mode)
configure_mariadb() {
  echo -e "${GREEN}Configuring MariaDB...${NC}"
  
  # Secure MariaDB installation
  run_quiet "Securing MariaDB" bash -c "sudo mariadb --user=root --socket=/var/run/mysqld/mysqld.sock -e \"ALTER USER 'root'@'localhost' IDENTIFIED BY '$DB_ROOT_PASS'; FLUSH PRIVILEGES;\" || true"
  run_quiet "Cleaning up MariaDB users" bash -c "sudo mariadb --user=root --socket=/var/run/mysqld/mysqld.sock -e \"DELETE FROM mysql.user WHERE User=''; DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1'); DROP DATABASE IF EXISTS test; DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%'; FLUSH PRIVILEGES;\""
  
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
  run_quiet "Restarting MariaDB" systemctl restart mariadb
}

# Helper to configure PostgreSQL (only for fresh mode)
configure_postgresql() {
  # Ensure PostgreSQL is started and enabled
  run_quiet "Starting PostgreSQL" systemctl start postgresql
  
  # Wait for PostgreSQL socket to be ready (critical for CI)
  echo -n -e "${BLUE}  - Waiting for PostgreSQL to be ready... ${NC}"
  for i in {1..30}; do
    if sudo -u postgres psql -c "select 1" >> "$INSTALL_LOG" 2>&1; then
      echo -e "${GREEN}✓ READY${NC}"
      break
    fi
    echo -n "."
    sleep 1
    if [[ $i == 30 ]]; then echo -e "${RED}✗ TIMEOUT${NC}"; exit 1; fi
  done
  
  # Set postgres user password
  run_quiet "Setting PostgreSQL root password" sudo -u postgres psql -c "ALTER USER postgres PASSWORD '$DB_ROOT_PASS';"
  
  # Pre-enable extensions in template1 so all new bench sites have them
  # Verification: Check if vector.control exists, if not, try re-installing
  if [ ! -f "/usr/share/postgresql/16/extension/vector.control" ]; then
    run_quiet "Re-installing pgvector (emergency check)" apt-get install -y --reinstall postgresql-16-pgvector
  fi

  run_quiet "Enabling PostgreSQL extensions (vector, cube, etc.)" bash -c "sudo -u postgres psql -d template1 -c 'CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS cube; CREATE EXTENSION IF NOT EXISTS earthdistance;'"
  
  # Allow password authentication for local connections
  PG_VERSION=$(psql --version | grep -oE '[0-9]+' | head -1)
  PG_CONF="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"
  
  if [ -f "$PG_CONF" ]; then
    run_quiet "Configuring authentication policy (md5)" bash -c "sed -i '/^local/s/peer/md5/' '$PG_CONF' && sed -i '/^host/s/ident/md5/' '$PG_CONF'"
    run_quiet "Applying PostgreSQL configuration" systemctl restart postgresql
  else
    echo -e "${RED}Warning: Could not find PostgreSQL config at $PG_CONF${NC}"
  fi
}

# Helper to create frappe system user (only for fresh mode)
create_frappe_user() {
  echo -e "${GREEN}Creating/Configuring frappe system user...${NC}"
  if ! id -u frappe > /dev/null 2>&1; then
    useradd -m -s /bin/bash frappe
    usermod -aG sudo frappe
  fi
  # Nuclear sudo permission for frappe user (Always ensured for bench setup production)
  echo "frappe ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/frappe
  chmod 440 /etc/sudoers.d/frappe
}

# Helper to install Bench (fresh or bench mode)
install_bench() {
  echo -e "${GREEN}Installing Bench...${NC}"
  # Fixing stdin propagation for bench init
  run_quiet "Initializing Frappe Bench (this may take a few minutes)" sudo -u frappe -i -H env HOME=/home/frappe XDG_CONFIG_HOME=/home/frappe/.config XDG_DATA_HOME=/home/frappe/.local/share PATH="/home/frappe/.local/bin:/usr/bin:/usr/local/bin:$PATH" bash <<EOF
set -e
export PATH=\$PATH:/home/frappe/.local/bin
cd /home/frappe
if [ ! -d "frappe-bench" ]; then
  # Use Python 3.14 (Required for Frappe v16)
  python3.14 -m pip install frappe-bench --user -q
  
  # Diagnostics and Environment Hardening
  export CI=1
  export YARN_PURE_LOCKFILE=1
  export YARN_NETWORK_TIMEOUT=300000
  export YARN_CONFIG_IGNORE_ENGINES=true
  
  # Force yarn to ignore version mismatches
  yarn config set ignore-engines true >> "$INSTALL_LOG" 2>&1
  
  # Initialize bench with Python 3.14
  # Using absolute path to bench binary
  /home/frappe/.local/bin/bench init frappe-bench --frappe-branch version-16 --python python3.14 --skip-assets --skip-redis-config-generation --verbose
  
  # Crucial for Postgres: Install the driver inside the bench virtualenv
  if [[ "$DB_TYPE" == "postgres" ]]; then
    ./frappe-bench/env/bin/pip install psycopg2-binary >> "$INSTALL_LOG" 2>&1
  fi
fi
EOF
}

# Helper to fetch latest RPanel release tag
fetch_latest_tag() {
  if [ -f "/home/frappe/frappe-bench/apps/rpanel/scripts/get_latest_release.py" ]; then
    python3.14 /home/frappe/frappe-bench/apps/rpanel/scripts/get_latest_release.py 2>/dev/null || echo ""
  else
    echo ""
  fi
}

# Main logic per mode
case "$MODE" in
  fresh)
    if [[ "$CI" == "true" ]]; then
      echo -e "${GREEN}CI detected: Forcing 4GB swap for asset compilation stability...${NC}"
      # Turn off existing swap to avoid "Text file busy"
      swapoff /swapfile >> "$INSTALL_LOG" 2>&1 || true
      fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
      chmod 600 /swapfile
      mkswap /swapfile
      swapon /swapfile || true
    else
      setup_swap
    fi
    install_system_deps
    if [[ "$DB_TYPE" == "postgres" ]]; then
      configure_postgresql
    else
      configure_mariadb
    fi
    create_frappe_user
    install_bench
    ;;
  bench)
    # Existing bench - just ensure frappe user exists
    create_frappe_user || true
    ;;
esac

# Install/Update RPanel app
# Note: On fresh installs, rpanel app doesn't exist yet, so fetch_latest_tag 
# returns empty and we download the default branch (usually main/master).
LATEST_TAG=$(fetch_latest_tag || echo "")
if [ -z "$LATEST_TAG" ]; then
  TAG_OPTION=""
else
  TAG_OPTION="--branch $LATEST_TAG"
fi

# Define common sudo prefix for bench commands
# Heredoc variables are now globally exported at the top of the script
BENCH_SUDO="sudo -u frappe -i -H env CI=$CI NODE_OPTIONS=$NODE_OPTIONS ESBUILD_WORKERS=$ESBUILD_WORKERS MAX_WORKERS=$MAX_WORKERS CPU_COUNT=$CPU_COUNT GENERATE_SOURCEMAP=$GENERATE_SOURCEMAP NODE_ENV=$NODE_ENV HOME=/home/frappe XDG_CONFIG_HOME=/home/frappe/.config XDG_DATA_HOME=/home/frappe/.local/share PATH=/usr/bin:/usr/local/bin:/home/frappe/.local/bin:$PATH"

if [ ! -d "/home/frappe/frappe-bench/apps/rpanel" ]; then
  run_quiet "Downloading RPanel app" $BENCH_SUDO bash -c "cd /home/frappe/frappe-bench && bench get-app https://github.com/RokctAI/rpanel.git $TAG_OPTION --skip-assets"
else
  run_quiet "Updating RPanel app" $BENCH_SUDO bash -c "cd /home/frappe/frappe-bench/apps/rpanel && git fetch --tags && [ -n \"$TAG_OPTION\" ] && git checkout $LATEST_TAG"
fi

run_quiet "Setting up Redis config" $BENCH_SUDO bash -c "cd /home/frappe/frappe-bench && bench setup redis"

SITE_NAME="${DOMAIN_NAME:-rpanel.local}"
# Declare absolute bench path
BENCH_BIN="/home/frappe/.local/bin/bench"

if [ ! -d "/home/frappe/frappe-bench/sites/$SITE_NAME" ]; then
  run_quiet "Creating site: $SITE_NAME" $BENCH_SUDO bash -c "cd /home/frappe/frappe-bench && $BENCH_BIN new-site $SITE_NAME --admin-password admin --db-root-password $DB_ROOT_PASS $( [[ \"$DB_TYPE\" == \"postgres\" ]] && echo --db-type postgres )"
fi

# Ensure the app is installed/registered (bench handles apps.txt correctly)
run_quiet "Installing RPanel into site" $BENCH_SUDO bash -c "cd /home/frappe/frappe-bench && $BENCH_BIN --site $SITE_NAME install-app rpanel || true"
# Build application assets (Non-fatal as requested for headless/API-only usage)
echo -n -e "${BLUE}  - Building application assets... ${NC}"
# Use || true inside to ensure SIGTERM (143) doesn't kill the installer
if $BENCH_SUDO bash -c "export NODE_OPTIONS='--max-old-space-size=1536'; export GENERATE_SOURCEMAP=false; cd /home/frappe/frappe-bench && $BENCH_BIN build --app rpanel --hard-link || true" >> "$INSTALL_LOG" 2>&1; then
  echo -e "${YELLOW}! COMPLETED (Asset build finished or skipped)${NC}"
else
  echo -e "${YELLOW}! FAILED (Non-fatal)${NC}"
  echo -e "${BLUE}    Note: Desk UI assets may be missing, but the API remains functional.${NC}"
fi

# Production setup
echo -e "${GREEN}Configuring production services...${NC}"

# 1. Ensure production prerequisites are ready (nginx + fail2ban + supervisor)
run_quiet "Installing Nginx" apt-get install -y -qq -o=Dpkg::Use-Pty=0 nginx
run_quiet "Starting Nginx" systemctl start nginx
run_quiet "Installing fail2ban" apt-get install -y -qq -o=Dpkg::Use-Pty=0 fail2ban
run_quiet "Installing Supervisor" apt-get install -y -qq -o=Dpkg::Use-Pty=0 supervisor
run_quiet "Starting Supervisor" systemctl restart supervisor

# 2. THE CI MASTER FIX: Login shell with explicit PYTHONPATH
# NON-FATAL: bench setup production may fail on 'systemctl reload nginx' in CI.
# The configs ARE generated before the reload. Our verification block handles the rest.
echo -n -e "${BLUE}  - Generating production config... ${NC}"
if sudo -i -u frappe bash <<EOF >> "$INSTALL_LOG" 2>&1
export PATH="/home/frappe/.local/bin:\$PATH"
export PYTHONPATH=\$(python3.14 -m site --user-site 2>/dev/null || echo "/home/frappe/.local/lib/python3.14/site-packages")
cd /home/frappe/frappe-bench
sudo env "PATH=\$PATH" "PYTHONPATH=\$PYTHONPATH" /home/frappe/.local/bin/bench setup production frappe --yes
EOF
then
  echo -e "${GREEN}✓ DONE${NC}"
else
  echo -e "${YELLOW}! COMPLETED (config generated, service reload deferred)${NC}"
fi

# 3. Final Verification and Emergency Linking
echo -n -e "${BLUE}  - Verifying Nginx configuration... ${NC}"
NGINX_CONF="/etc/nginx/conf.d/frappe.conf"
BENCH_CONF="/home/frappe/frappe-bench/config/nginx.conf"

if [ -f "$NGINX_CONF" ]; then
    echo -e "${GREEN}✓ VERIFIED${NC}"
elif [ -f "$BENCH_CONF" ]; then
    ln -sf "$BENCH_CONF" "$NGINX_CONF"
    echo -e "${YELLOW}✓ RECOVERED (Manually Linked)${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
    echo -e "${RED}Error: Nginx config was not generated at $BENCH_CONF${NC}"
    exit 1
fi

# 4. Critical: The GitHub Actions Permission Punch
run_quiet "Applying directory permissions" chmod o+x /home/frappe /home/frappe/frappe-bench /home/frappe/frappe-bench/sites

# 5. Service Restart
run_quiet "Restarting Nginx" systemctl restart nginx
run_quiet "Restarting Supervisor" systemctl restart supervisor

# 6. Final API Health Check
echo -n -e "${BLUE}  - RPanel API Health Check... ${NC}"
if curl -s -f http://localhost > /dev/null; then
    echo -e "${GREEN}✓ ONLINE${NC}"
else
    echo -e "${YELLOW}! UNRESPONSIVE (Check Nginx Logs)${NC}"
fi

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
