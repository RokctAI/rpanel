#!/bin/bash

# RPanel Flexible Installer
# Usage: DEPLOY_MODE=[fresh|bench|dependency] ./install.sh
# Default mode is "fresh" (full VPS install).
INSTALLER_VERSION="v8.9.3-STABLE"

echo -e "\033[0;34mRPanel Installer Version: $INSTALLER_VERSION\033[0;0m"

# Fail on error, but be careful with piped commands
set -e
set -o pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0;0m'

# Global Build Hardening
export CI=${CI:-true}
export DEBIAN_FRONTEND=noninteractive
# Use 1.5GB to force more aggressive GC.
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

# Hardcoded administrative password
DB_ROOT_PASS="rpanel_secure_db_pass"

# Determine deployment mode
MODE="${DEPLOY_MODE:-fresh}"
DB_TYPE="${DB_TYPE:-postgres}"

if [[ "$MODE" != "fresh" && "$MODE" != "bench" ]]; then
  echo -e "${RED}Invalid DEPLOY_MODE: $MODE. Use 'fresh' or 'bench'.${NC}"
  exit 1
fi

echo -e "${GREEN}Deploy mode: $MODE${NC}"

# Detect OS
if [ -f /etc/os-release ]; then
  . /etc/os-release
  DISTRO=$ID
  CODENAME=$VERSION_CODENAME
else
  echo -e "${RED}Unsupported OS: /etc/os-release not found.${NC}"
  exit 1
fi

# Fallback for Debian if codename is empty
if [[ "$DISTRO" == "debian" && -z "$CODENAME" ]]; then
  CODENAME="bookworm"
fi

# Define Python binary globally
# Define Python binary globally
if [[ -z "$PYTHON_BIN" ]]; then
  # 1. Try to find existing 3.14
  if command -v python3.14 >/dev/null 2>&1; then
    PYTHON_BIN="python3.14"
  # 2. Try to use uv to install/find 3.14 (essential for Frappe v16+)
  else
    echo -e "${BLUE}  - Bootstrapping Python 3.14 via uv...${NC}"
    if ! command -v uv >/dev/null 2>&1; then
      curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh >>"$INSTALL_LOG" 2>&1 || true
    fi
    if command -v uv >/dev/null 2>&1; then
      # Ensure uv is in the path for the current shell
      export PATH="/usr/local/bin:$PATH"
      uv python install 3.14 >>"$INSTALL_LOG" 2>&1 || true
      PYTHON_BIN=$(uv python find 3.14 2>/dev/null || echo "")
    fi
  fi

  # Fallback logic if 3.14 bootstrap failed
  if [[ -z "$PYTHON_BIN" ]]; then
    if command -v python3.13 >/dev/null 2>&1; then
      PYTHON_BIN="python3.13"
    elif command -v python3.12 >/dev/null 2>&1; then
      PYTHON_BIN="python3.12"
    elif [[ "$DISTRO" == "ubuntu" ]] || [[ "$CODENAME" == "trixie" ]]; then
      PYTHON_BIN="python3.14"
    elif [[ "$DISTRO" == "debian" && "$CODENAME" == "bookworm" ]]; then
      PYTHON_BIN="python3.12"
    else
      PYTHON_BIN="python3"
    fi
  fi
fi

# Non-interactive mode for CI
if [[ "$CI" == "true" || "$NON_INTERACTIVE" == "true" ]]; then
  echo -e "${GREEN}CI/Non-interactive environment detected. Using defaults.${NC}"
  DOMAIN_NAME=${DOMAIN_NAME:-rpanel.local}
  SELF_HOSTED=${SELF_HOSTED:-Y}
  SKIP_SSL=true
else
  # Prompt for domain in fresh mode
  if [[ "$MODE" == "fresh" ]]; then
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}Domain Configuration${NC}"
    echo -e "${BLUE}=================================================${NC}"
    read -p "Enter your domain name (or press Enter for rpanel.local): " DOMAIN_NAME
    DOMAIN_NAME=${DOMAIN_NAME:-rpanel.local}

    echo -e "${BLUE}Hosting Mode${NC}"
    echo "Will this server also host websites?"
    read -p "Host websites on this server? (Y/n): " SELF_HOSTED
    SELF_HOSTED=${SELF_HOSTED:-Y}
  fi
fi

# Helper to run commands quietly but log details
run_quiet() {
  local msg="$1"
  shift
  echo -n -e "${BLUE}  - $msg... ${NC}"
  if "$@" >>"$INSTALL_LOG" 2>&1; then
    echo -e "${GREEN}✓ DONE${NC}"
  else
    echo -e "${RED}✗ FAILED${NC}"
    echo -e "${RED}Check $INSTALL_LOG for details.${NC}"
    tail -n 20 "$INSTALL_LOG" | sed 's/^/    /'
    exit 1
  fi
}

# Helper to setup swap
setup_swap() {
  if [[ "$MODE" == "fresh" ]]; then
    if swapon --show | grep -q "/swapfile"; then
      echo -e "${BLUE}  - Swap already exists.${NC}"
      return
    fi

    local total_mem
    total_mem=$(free -m | awk '/^Mem:/{print $2}')
    if [[ -n "$total_mem" && ("$total_mem" -lt 4000 || "$CI" == "true") ]]; then
      local swap_size="2G"
      [[ "$CI" == "true" ]] && swap_size="4G"
      echo -e "${GREEN}Creating $swap_size swap file...${NC}"
      # Fallback to dd if fallocate fails (e.g. on some filesystems)
      fallocate -l "$swap_size" /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=$([[ "$swap_size" == "4G" ]] && echo 4096 || echo 2048)
      chmod 600 /swapfile
      mkswap /swapfile >>"$INSTALL_LOG" 2>&1
      swapon /swapfile >>"$INSTALL_LOG" 2>&1 || echo -e "${YELLOW}Warning: Could not enable swap (likely in a container). Continuing...${NC}"
      if ! grep -q "/swapfile" /etc/fstab; then
        echo "/swapfile swap swap defaults 0 0" >>/etc/fstab
      fi
    fi
  fi
}

# Helper to install system packages
install_system_deps() {
  run_quiet "Updating package lists" apt-get update
  run_quiet "Installing basic tools" apt-get install -y curl ca-certificates gnupg software-properties-common build-essential pkg-config git cron
  mkdir -p /etc/apt/keyrings

  # PHP PPA
  if [[ "$DISTRO" == "ubuntu" ]]; then
    run_quiet "Adding PHP PPA" add-apt-repository -y ppa:ondrej/php
  else
    run_quiet "Adding Sury PHP Repo" bash -c "curl -fsSL https://packages.sury.org/php/apt.gpg | gpg --dearmor -o /etc/apt/keyrings/sury-php.gpg && \
            echo \"deb [signed-by=/etc/apt/keyrings/sury-php.gpg] https://packages.sury.org/php/ $CODENAME main\" > /etc/apt/sources.list.d/sury-php.list"
  fi

  # PostgreSQL PGDG Repo
  run_quiet "Adding PostgreSQL Repo" bash -c "curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg && \
        echo \"deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $CODENAME-pgdg main\" > /etc/apt/sources.list.d/pgdg.list"

  if [[ "$DISTRO" == "ubuntu" ]]; then
    run_quiet "Adding Python PPA" add-apt-repository -y ppa:deadsnakes/ppa
  elif [[ "$DISTRO" == "debian" && "$CODENAME" == "bookworm" ]]; then
    run_quiet "Adding Debian Backports" bash -c "echo 'deb http://deb.debian.org/debian bookworm-backports main' > /etc/apt/sources.list.d/backports.list"
  fi

  run_quiet "Updating package lists after repo additions" apt-get update --fix-missing || (sleep 2 && apt-get update)

  # Common dependencies
  local packages=(
    redis-server
    xvfb
    libfontconfig
    libjpeg-dev
    zlib1g-dev
    default-libmysqlclient-dev
    python3-pip
    python-is-python3
    exim4
    exim4-daemon-heavy
    opendkim
    opendkim-tools
    certbot
    python3-certbot-nginx
    fail2ban
    supervisor
    nginx
    unattended-upgrades
    cron
  )

  # Python Dev Headers (only if not using uv managed python)
  if [[ "$PYTHON_BIN" == "/usr/bin/python3.14" || "$PYTHON_BIN" == "python3.14" ]]; then
    packages+=(python3.14-dev python3.14-venv)
  elif [[ "$PYTHON_BIN" == "/usr/bin/python3.12" || "$PYTHON_BIN" == "python3.12" ]]; then
    packages+=(python3.12-dev python3.12-venv)
  elif [[ "$PYTHON_BIN" == "python3" ]]; then
    packages+=(python3-dev python3-venv)
  fi

  if [[ "$DB_TYPE" == "postgres" ]]; then
    packages+=(postgresql-16 postgresql-client-16 postgresql-contrib-16 postgresql-16-pgvector libpq-dev)
  else
    packages+=(mariadb-server mariadb-client)
  fi

  run_quiet "Installing system dependencies" apt-get install -y "${packages[@]}"

  # Install wkhtmltopdf
  if [[ "$DISTRO" == "ubuntu" && "$CODENAME" == "noble" ]]; then
    # Noble: install libjpeg62-turbo compatibility shim first
    run_quiet "Installing libjpeg62-turbo shim" bash -c "
            curl -fsSL -o /tmp/libjpeg.deb \
            http://archive.ubuntu.com/ubuntu/pool/main/libj/libjpeg-turbo/libjpeg62-turbo_2.1.5-2ubuntu1_amd64.deb \
            && dpkg -i /tmp/libjpeg.deb \
            && rm /tmp/libjpeg.deb"
    run_quiet "Installing wkhtmltopdf manually" bash -c "
            curl -fsSL -o /tmp/wkhtmltopdf.deb \
            https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
            && apt-get install -y /tmp/wkhtmltopdf.deb \
            && rm /tmp/wkhtmltopdf.deb"
  elif [[ "$DISTRO" == "ubuntu" ]]; then
    # Older Ubuntu: wkhtmltopdf is in the native repos
    run_quiet "Installing wkhtmltopdf" apt-get install -y wkhtmltopdf
  else
    # Debian trixie: use bookworm .deb, libjpeg62-turbo is available natively
    run_quiet "Installing wkhtmltopdf manually" bash -c "
            curl -fsSL -o /tmp/wkhtmltopdf.deb \
            https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
            && apt-get install -y /tmp/wkhtmltopdf.deb \
            && rm /tmp/wkhtmltopdf.deb"
  fi

  # Node.js (Standardize on NodeSource Repo style)
  run_quiet "Adding NodeSource GPG key" bash -c "curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg"
  run_quiet "Adding NodeSource Repo" bash -c "echo \"deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main\" > /etc/apt/sources.list.d/nodesource.list"
  run_quiet "Updating package lists for Node.js" apt-get update
  run_quiet "Installing Node.js" apt-get install -y nodejs
  run_quiet "Installing Yarn" npm install -g yarn
  run_quiet "Configuring Yarn global policy" yarn config set ignore-engines true -g

  # Configure automatic security updates
  if [[ "$CI" != "true" ]]; then
    echo -e "${GREEN}Configuring automatic security updates...${NC}"
    cat >/etc/apt/apt.conf.d/50unattended-upgrades <<EOF
Unattended-Upgrade::Allowed-Origins {
    "\${distro_id}:\${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF
    cat >/etc/apt/apt.conf.d/20auto-upgrades <<EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
    systemctl enable unattended-upgrades || true
    systemctl start unattended-upgrades || true
  fi
}

configure_exim4() {
  run_quiet "Configuring Exim4" bash -c "debconf-set-selections <<EOF
exim4-config exim4/dc_eximconfig_configtype select internet site; mail is sent and received directly using SMTP
exim4-config exim4/dc_other_hostnames string
exim4-config exim4/dc_local_interfaces string 127.0.0.1 ; ::1
EOF
    dpkg-reconfigure -f noninteractive exim4-config"
  systemctl enable exim4 >>"$INSTALL_LOG" 2>&1 || true
  systemctl start exim4 >>"$INSTALL_LOG" 2>&1 || true
}

configure_postgresql() {
  systemctl start postgresql >>"$INSTALL_LOG" 2>&1 || true
  echo -n -e "${BLUE}  - Waiting for PostgreSQL... ${NC}"
  for i in {1..30}; do
    if sudo -u postgres psql -c "select 1" >/dev/null 2>&1; then
      echo -e "${GREEN}✓ READY${NC}"
      break
    fi
    sleep 1
    [[ $i == 30 ]] && {
      echo -e "${RED}✗ TIMEOUT${NC}"
      exit 1
    }
  done

  run_quiet "Setting PostgreSQL password" sudo -u postgres psql -c "ALTER USER postgres PASSWORD '$DB_ROOT_PASS';"
  run_quiet "Enabling extensions in template1" sudo -u postgres psql -d template1 -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS cube; CREATE EXTENSION IF NOT EXISTS earthdistance;"

  local pg_hba
  pg_hba=$(sudo -u postgres psql -t -P format=unaligned -c "show hba_file;")
  if [[ -f "$pg_hba" ]]; then
    run_quiet "Configuring pg_hba.conf" bash -c "sed -i '/^local/s/peer/md5/' '$pg_hba' && sed -i '/^host/s/ident/md5/' '$pg_hba'"
    systemctl restart postgresql >>"$INSTALL_LOG" 2>&1 || true
  fi
}

configure_mariadb() {
  systemctl start mariadb >>"$INSTALL_LOG" 2>&1 || true
  run_quiet "Securing MariaDB" mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '$DB_ROOT_PASS'; DELETE FROM mysql.user WHERE User=''; DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1'); DROP DATABASE IF EXISTS test; DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%'; FLUSH PRIVILEGES;"
  cat >/root/.my.cnf <<EOF
[client]
user=root
password=$DB_ROOT_PASS
EOF
  chmod 600 /root/.my.cnf

  # Configure MariaDB for Frappe
  cat >/etc/mysql/mariadb.conf.d/frappe.cnf <<EOF
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

create_frappe_user() {
  if ! id -u frappe >/dev/null 2>&1; then
    useradd -m -s /bin/bash frappe
    usermod -aG sudo frappe
  fi
  echo "frappe ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/frappe
  chmod 440 /etc/sudoers.d/frappe
}

install_bench() {
  run_quiet "Installing frappe-bench" sudo -u frappe -i bash -c "export PATH=\$PATH:/home/frappe/.local/bin; python3 -m pip install frappe-bench --user --break-system-packages || python3 -m pip install frappe-bench --user"

  run_quiet "Initializing frappe-bench" sudo -u frappe -i bash -c "set -e; export PATH=\"\$PATH:/home/frappe/.local/bin\"; cd /home/frappe; if [ ! -d \"frappe-bench\" ]; then bench init frappe-bench --frappe-branch version-16 --python $PYTHON_BIN --skip-assets --skip-redis-config-generation; fi; if [[ \"$DB_TYPE\" == \"postgres\" ]]; then ./frappe-bench/env/bin/pip install psycopg2-binary; fi"
}

fetch_latest_tag() {
  if [ -f "/home/frappe/frappe-bench/apps/rpanel/scripts/get_latest_release.py" ]; then
    sudo -u frappe "$PYTHON_BIN" /home/frappe/frappe-bench/apps/rpanel/scripts/get_latest_release.py 2>/dev/null || echo ""
  else
    echo ""
  fi
}

# Main installation flow
case "$MODE" in
fresh)
  setup_swap
  install_system_deps
  configure_exim4
  if [[ "$DB_TYPE" == "postgres" ]]; then
    configure_postgresql
  else
    configure_mariadb
  fi
  create_frappe_user
  install_bench
  ;;
bench)
  create_frappe_user
  ;;
esac

# RPanel App Installation
echo -e "${GREEN}Installing/Updating RPanel app...${NC}"
LATEST_TAG=$(fetch_latest_tag || echo "")
TAG_OPTION=""
[ -n "$LATEST_TAG" ] && TAG_OPTION="--branch $LATEST_TAG"

run_quiet "Installing RPanel app" sudo -u frappe -i bash -c "set -e; export PATH=\"\$PATH:/home/frappe/.local/bin\"; cd /home/frappe/frappe-bench; if [ ! -d \"apps/rpanel\" ]; then bench get-app https://github.com/RokctAI/rpanel.git $TAG_OPTION --skip-assets; else cd apps/rpanel && git fetch --tags && ([ -n \"$LATEST_TAG\" ] && git checkout \"$LATEST_TAG\" || git pull); cd ../..; fi; if [ ! -d \"sites/${DOMAIN_NAME:-rpanel.local}\" ]; then bench new-site --admin-password admin --db-root-password \"$DB_ROOT_PASS\" $([[ \"$DB_TYPE\" == \"postgres\" ]] && echo \"--db-type=postgres\") --force \"${DOMAIN_NAME:-rpanel.local}\"; fi; $PYTHON_BIN -c \"import os; f='sites/apps.txt'; apps=open(f).read().splitlines() if os.path.exists(f) else []; (apps.append('rpanel') if 'rpanel' not in apps else None); open(f, 'w').write('\\n'.join(apps) + '\\n')\"; bench --site \"${DOMAIN_NAME:-rpanel.local}\" install-app rpanel; bench setup redis"

# Asset build
if [[ "$SKIP_ASSETS" != "true" ]]; then
  run_quiet "Building assets" sudo -u frappe -i bash -c "cd /home/frappe/frappe-bench && export NODE_OPTIONS='--max-old-space-size=2048' && /home/frappe/.local/bin/bench build --app rpanel --hard-link"
else
  echo -e "${YELLOW}  - Skipping asset build (Headless mode)...${NC}"
fi

# Production setup
run_quiet "Setting up production" sudo -u frappe -i bash -c "cd /home/frappe/frappe-bench && sudo /home/frappe/.local/bin/bench setup production frappe --yes"

# Fix permissions
run_quiet "Fixing permissions" chmod o+x /home/frappe /home/frappe/frappe-bench /home/frappe/frappe-bench/sites

# Final health check and services
systemctl restart nginx >>"$INSTALL_LOG" 2>&1 || true
systemctl restart supervisor >>"$INSTALL_LOG" 2>&1 || true

# Provision localhost if self-hosted
if [[ "$SELF_HOSTED" =~ ^[Yy]$ ]]; then
  run_quiet "Provisioning localhost" bash /home/frappe/frappe-bench/apps/rpanel/scripts/provision_localhost.sh
fi

# Setup SSL if domain is not localhost/rpanel.local
if [[ "$MODE" == "fresh" && "$DOMAIN_NAME" != "rpanel.local" && "$DOMAIN_NAME" != "localhost" && "$SKIP_SSL" != "true" ]]; then
  echo -e "${GREEN}Setting up SSL for $DOMAIN_NAME...${NC}"
  certbot --nginx -d "$DOMAIN_NAME" --non-interactive --agree-tos --register-unsafely-without-email || {
    echo -e "${RED}SSL setup failed. You can run 'sudo certbot --nginx -d $DOMAIN_NAME' manually later.${NC}"
  }
fi

echo -e "${GREEN}Installation complete!${NC}"
echo -e "${BLUE}Site: ${DOMAIN_NAME:-rpanel.local}${NC}"
echo -e "${BLUE}Admin Password: admin${NC}"
