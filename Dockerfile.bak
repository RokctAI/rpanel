# Stage 1: Base - System Dependencies & Bench Setup
FROM python:3.14-slim AS base

# System Dependencies (Frappe + MariaDB + PDF + Build Tools)
RUN apt-get update && apt-get install -y \
    git mariadb-client postgresql-client gettext-base wget libssl-dev \
    fonts-cantarell xvfb libfontconfig wkhtmltopdf \
    python3-dev python3-setuptools python3-pip python3-distutils build-essential \
    cron curl vim nodejs npm redis-server software-properties-common \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g yarn
RUN useradd -ms /bin/bash frappe

# Bench Setup
USER frappe
WORKDIR /home/frappe
RUN pip3 install frappe-bench
RUN bench init --skip-assets --skip-redis-config-generation --python python3 frappe-bench

WORKDIR /home/frappe/frappe-bench

# Stage 2: Lean - The Core App & Python Environment (Drone/API Target)
FROM base AS lean

# INJECT CI ARTIFACTS or Local Source
COPY --chown=frappe:frappe apps ./apps

# Install All Apps in editable mode
RUN for app in $(ls apps); do \
    bench pip install -e apps/$app; \
    done

# Build Assets (JS/CSS)
RUN bench build

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
