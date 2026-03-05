# Stage 1: Base - System Dependencies & Bench Setup
ARG UBUNTU_VERSION=24.04
FROM ubuntu:${UBUNTU_VERSION} AS base

# Define Build Arguments
ARG GITHUB_TOKEN
ARG IS_ROKCTAI_REPO=false

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# System Dependencies (Frappe + PostgreSQL + PDF + Build Tools)
# Includes dependencies previously installed by install_stack.py (libxml2-dev, libxslt1-dev)
RUN apt-get update && apt-get install -y software-properties-common lsb-release curl ca-certificates gnupg sudo \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/keyrings/postgresql.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_24.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y \
    git postgresql-16 postgresql-16-pgvector postgresql-client gettext-base wget libssl-dev \
    fonts-cantarell xvfb libfontconfig \
    python3.14 python3.14-dev python3.14-venv \
    python3-pip python3-setuptools build-essential \
    cron vim nodejs redis-server \
    libffi-dev libjpeg-dev zlib1g-dev \
    libcairo2-dev libpango1.0-dev pkg-config \
    libxml2-dev libxslt1-dev \
    && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb -O /tmp/wkhtmltox.deb \
    && apt-get install -y /tmp/wkhtmltox.deb || true \
    && rm -f /tmp/wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g yarn pnpm
RUN useradd -ms /bin/bash frappe

# Bench Setup
USER frappe
WORKDIR /home/frappe
ENV PATH="/home/frappe/.local/bin:${PATH}"

# Install Bench
RUN pip3 install --break-system-packages frappe-bench

# Stage 2: Native App Installation (The Builder)
FROM base AS builder

USER root
# Map platform.rokct.ai to 127.0.0.1 for local site access
RUN echo "127.0.0.1 platform.rokct.ai" >> /etc/hosts
# We need Git for bench get-app
# Configure Git to use the token for private repo access
RUN git config --global url."https://x-access-token:${GITHUB_TOKEN}@github.com/".insteadOf "git@github.com:" && \
    git config --global url."https://x-access-token:${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"
USER frappe

# Inject Context
# These are provided by build.yml checkout steps
COPY --chown=frappe:frappe monorepo_overrides /home/frappe/monorepo_overrides
COPY --chown=frappe:frappe control_app /home/frappe/control_app

# The CURRENT Repository's code (Whatever repo is invoking the Docker build)
# This is equivalent to GITHUB_WORKSPACE in CI
COPY --chown=frappe:frappe current_repo /home/frappe/current_repo

# Apply Bench Overrides
RUN if [ -d "/home/frappe/monorepo_overrides/bench" ]; then \
    echo "Applying Bench Overrides from Monorepo..."; \
    BENCH_PATH=$(python3 -c "import bench; import os; print(os.path.dirname(bench.__file__))"); \
    cp -r /home/frappe/monorepo_overrides/bench/bench/* "$BENCH_PATH/"; \
    fi

# Initialize Bench
RUN bench init --skip-assets --skip-redis-config-generation --frappe-branch version-16 --python python3.14 frappe-bench

WORKDIR /home/frappe/frappe-bench

# 1. Sync Workspace Code to Bench Apps and Register
RUN APP_NAME=$(cat /home/frappe/current_repo/pyproject.toml 2>/dev/null | grep -m1 'name = "' | cut -d'"' -f2 || echo "app") && \
    APP_DIR=$(echo "$APP_NAME" | tr '[:upper:]' '[:lower:]') && \
    echo "Syncing workspace code into apps/$APP_DIR..." && \
    mkdir -p "apps/$APP_DIR" && \
    cp -a /home/frappe/current_repo/. "apps/$APP_DIR/" && \
    echo "Registering $APP_NAME in Bench..." && \
    bench pip install -e "apps/$APP_DIR"

# Start required background services (Redis and PostgreSQL) for Installation
USER root
RUN service redis-server start && \
    service postgresql start && \
    su - postgres -c "psql -c \"ALTER USER postgres PASSWORD 'admin';\"" && \
    su - postgres -c "psql -d template1 -c 'CREATE EXTENSION IF NOT EXISTS vector;'" && \
    su - postgres -c "psql -d template1 -c 'CREATE EXTENSION IF NOT EXISTS cube;'" && \
    su - postgres -c "psql -d template1 -c 'CREATE EXTENSION IF NOT EXISTS earthdistance;'"

USER frappe
# Configure bench to hit local services
RUN bench set-config -g db_host 127.0.0.1 && \
    bench set-config -g redis_cache redis://127.0.0.1:6379 && \
    bench set-config -g redis_queue redis://127.0.0.1:6379 && \
    bench set-config -g redis_socketio redis://127.0.0.1:6379

# Create Site (Requires PostgreSQL running)
USER root
RUN service redis-server start && service postgresql start && \
    sudo -Eu frappe bash -c "export PATH=/home/frappe/.local/bin:\$PATH && cd /home/frappe/frappe-bench && bench new-site platform.rokct.ai --db-type postgres --db-root-password admin --admin-password admin || true && echo 'platform.rokct.ai' > sites/currentsite.txt"

# 2. Install Core App (The one we just synced)
RUN service redis-server start && service postgresql start && \
    sudo -Eu frappe bash -c "export PATH=/home/frappe/.local/bin:\$PATH && cd /home/frappe/frappe-bench && \
    APP_NAME=\$(cat /home/frappe/current_repo/pyproject.toml 2>/dev/null | grep -m1 'name = \"' | cut -d'\"' -f2 || echo 'app') && \
    echo \"Installing \$APP_NAME natively to site...\" && \
    bench --site platform.rokct.ai install-app \"\$APP_NAME\""

# 3. Install ERPNext (Standard Dependency, exactly like CI)
RUN service redis-server start && service postgresql start && \
    sudo -Eu frappe bash -c "export PATH=/home/frappe/.local/bin:\$PATH && cd /home/frappe/frappe-bench && bench get-app erpnext --branch version-16 --resolve-deps --skip-assets"

# 4. Install Control natively from local context
RUN service redis-server start && service postgresql start && \
    sudo -Eu frappe bash -c 'export PATH=/home/frappe/.local/bin:$PATH && cd /home/frappe/frappe-bench && \
    if [ "$IS_ROKCTAI_REPO" = "true" ] && [ -d "/home/frappe/control_app" ]; then \
    echo "Installing Local Control App..."; \
    mkdir -p apps/control; \
    cp -r /home/frappe/control_app/. apps/control/; \
    bench pip install -e apps/control; \
    if [ -d "/home/frappe/monorepo_overrides/control" ]; then \
    echo "Applying Monorepo Overrides to Control..."; \
    cp -rf /home/frappe/monorepo_overrides/control/. apps/control/; \
    fi; \
    else \
    echo "Installing Control Panel via HTTPS (Token-based)..."; \
    bench get-app https://x-access-token:${GITHUB_TOKEN}@github.com/RokctAI/control.git --resolve-deps --skip-assets; \
    fi; \
    bench --site platform.rokct.ai install-app control'

# Stage Monorepo Overrides for Install Stack
USER frappe
RUN if [ -d "/home/frappe/monorepo_overrides" ]; then \
    echo "Staging Monorepo Overrides for Install Stack..."; \
    cp -r /home/frappe/monorepo_overrides ./monorepo_overrides; \
    fi

# Run Native Stack Installation (Installs rcore, payments, etc with their OS deps)
USER root
RUN echo "127.0.0.1 platform.rokct.ai" >> /etc/hosts && \
    service redis-server start && service postgresql start && \
    sudo -Eu frappe bash -c "export PATH=/home/frappe/.local/bin:\$PATH && cd /home/frappe/frappe-bench && \
    echo 'Running Native Stack Installer...' && \
    python apps/control/install_stack.py platform.rokct.ai && \
    echo 'Generating Golden DB Seed...' && \
    bench --site platform.rokct.ai backup && \
    BACKUP_FILE=\$(ls sites/platform.rokct.ai/private/backups/*-database.sql.gz | head -n 1) && \
    if [ -f \"\$BACKUP_FILE\" ]; then \
    echo 'Backup found: '\$BACKUP_FILE; \
    mkdir -p apps/seed_data; \
    cp \"\$BACKUP_FILE\" \"apps/seed_data/seed.sql.gz\"; \
    echo '✅ Golden Seed created at apps/seed_data/seed.sql.gz'; \
    fi"

# Stage 3: Lean - The Core App & Python Environment (Drone/API Target)
FROM builder AS lean

# Assets are intentionally not built as this deployment is headless.

# Setup Entrypoint
USER root
COPY --chown=frappe:frappe docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
USER frappe

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["bench", "start"]

# Stage 3: Full - The "Batteries-Included" Image (VPS Target)
FROM lean AS full

USER root
# Install Web and Mail Services
RUN apt-get update && apt-get install -y \
    nginx exim4-daemon-heavy opendkim opendkim-tools \
    && rm -rf /var/lib/apt/lists/*

# Pre-configure Exim4 for internet mail
RUN debconf-set-selections <<EOF
exim4-config exim4/dc_eximconfig_configtype select internet site; mail is sent and received directly using SMTP
exim4-config exim4/dc_other_hostnames string
exim4-config exim4/dc_local_interfaces string 127.0.0.1 ; ::1
EOF

# Ensure Nginx logs can be written by anybody (for container safety)
RUN chmod -R 777 /var/log/nginx /var/lib/nginx

USER frappe
