# Copyright 2024 RokctAI
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
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y \
    git postgresql-16 postgresql-16-pgvector postgresql-client gettext-base wget libssl-dev \
    fonts-cantarell xvfb libfontconfig \
    python3.14 python3.14-dev python3.14-venv \
    python3-pip python3-setuptools build-essential \
    cron vim nodejs redis-server netcat-openbsd \
    libffi-dev libjpeg-dev zlib1g-dev \
    libcairo2-dev libpango1.0-dev pkg-config \
    libxml2-dev libxslt1-dev default-libmysqlclient-dev \
    && wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb -O /tmp/wkhtmltox.deb \
    && apt-get install -y /tmp/wkhtmltox.deb || true \
    && rm -f /tmp/wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g yarn pnpm
RUN useradd -ms /bin/bash frappe && \
    usermod -aG sudo frappe && \
    echo "frappe ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/frappe && \
    chmod 0440 /etc/sudoers.d/frappe

# Bench Setup
USER frappe
WORKDIR /home/frappe
ENV PATH="/home/frappe/.local/bin:${PATH}"

# Install Bench
RUN pip3 install --break-system-packages frappe-bench

# Stage 2: Native App Installation (The Builder)
FROM base AS builder

USER root
# We need Git for bench get-app
# Configure Git to use the token for private repo access
RUN git config --global url."https://x-access-token:${GITHUB_TOKEN}@github.com/".insteadOf "git@github.com:" && \
    git config --global url."https://x-access-token:${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"
USER frappe

# Inject Context
# These are provided by build.yml checkout steps
COPY --chown=frappe:frappe monorepo_overrides /home/frappe/monorepo_overrides

# The CURRENT Repository's code (Whatever repo is invoking the Docker build)
# This is equivalent to GITHUB_WORKSPACE in CI
COPY --chown=frappe:frappe current_repo /home/frappe/current_repo

# Apply Bench Overrides
RUN if [ -d "/home/frappe/monorepo_overrides/bench" ]; then \
    echo "Applying Bench Overrides from Monorepo..."; \
    BENCH_PATH=$(python3 -c "import bench; import os; print(os.path.dirname(bench.__file__))"); \
    cp -r /home/frappe/monorepo_overrides/bench/bench/* "$BENCH_PATH/"; \
    fi

# --- 2. Golden Ecosystem Build ---
USER root
# Download Golden Build Script
RUN wget -qO /usr/local/bin/build_ecosystem.sh https://raw.githubusercontent.com/RokctAI/shared-workflows/main/scripts/build_ecosystem.sh && \
    chmod +x /usr/local/bin/build_ecosystem.sh

USER frappe
WORKDIR /home/frappe

# Execute Golden Build
# Variables passed via environment or defaults in script
ARG RUN_TESTS=false
RUN export BOOTSTRAP=true && \
    export DB_TYPE=postgres && \
    export DB_PW=admin && \
    export GITHUB_TOKEN=${GITHUB_TOKEN} && \
    export RUN_TESTS=${RUN_TESTS} && \
    export APP_NAME=$(cat /home/frappe/current_repo/pyproject.toml 2>/dev/null | grep -m1 'name = "' | cut -d'"' -f2 || echo "rpanel") && \
    /usr/local/bin/build_ecosystem.sh


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
