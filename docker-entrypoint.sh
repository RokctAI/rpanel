#!/bin/bash
set -e

# Configuration
SITE_NAME=${SITE_NAME:-platform.rokct.ai}
MODE=${MODE:-full} # full, api, iot

echo "🚀 Starting RPanel in MODE: $MODE"

# Function to setup the site based on MODE
setup_site() {
  if [ ! -d "sites/$SITE_NAME" ]; then
    echo "🔥 Site '$SITE_NAME' not found. Starting Fresh Install..."

    # 1. Base Installation
    if [ -f "apps/seed_data/seed.sql.gz" ]; then
      echo "✨ Golden Seed Found! Restoring..."
      # Note: We still install 'rpanel' by default as the base, unless in iot mode
      INSTALL_APPS="rpanel"
      if [ "$MODE" = "iot" ]; then INSTALL_APPS="brain"; fi

      bench new-site "$SITE_NAME" \
        --source-sql "apps/seed_data/seed.sql.gz" \
        --admin-password "${ADMIN_PASSWORD:-admin}" \
        --db-root-password "${DB_ROOT_PASSWORD:-admin}" \
        --install-app "$INSTALL_APPS" \
        --force
    else
      echo "⚠️ No Golden Seed found. Doing standard clean install..."
      INSTALL_APPS="rpanel"
      if [ "$MODE" = "iot" ]; then INSTALL_APPS="brain"; fi

      bench new-site "$SITE_NAME" \
        --admin-password "${ADMIN_PASSWORD:-admin}" \
        --db-root-password "${DB_ROOT_PASSWORD:-admin}" \
        --install-app "$INSTALL_APPS"
    fi

    # 2. Sequential App Installation (Mode Dependent)
    # If not in iot mode, install the full suite
    if [ "$MODE" != "iot" ]; then
      echo "📦 Installing Full Suite (paas, rcore, control)..."
      bench --site "$SITE_NAME" install-app paas rcore control
    else
      echo "🛸 IoT Isolation: Installing Brain & RCore only..."
      # Note: rpanel is excluded to prevent Control Mode interference
      bench --site "$SITE_NAME" install-app rcore
    fi

    bench use "$SITE_NAME"
  else
    echo "✅ Site '$SITE_NAME' already exists."
  fi
}

# Function to start services
start_services() {
  case "$MODE" in
  "full")
    echo "💻 Full Mode: Starting everything..."
    # Start Exim4 and Nginx if we are root
    if [ "$(id -u)" = "0" ]; then
      service exim4 start || true
      nginx -g 'daemon off;' &
      # Switch to frappe for bench
      exec su-exec frappe bench start
    else
      # If already frappe user, just start bench (Nginx/Exim must be handled via sidecars or sudo)
      exec bench start
    fi
    ;;
  "api")
    echo "🔌 API Mode: Starting Gunicorn + Workers (Headless)..."
    # We don't use 'bench start' because it includes Node/SocketIO in standard Procfile
    bench worker &
    bench schedule &
    # Run Gunicorn directly for the API
    exec bench serve --port 8000
    ;;
  "iot")
    echo "🔋 IoT Mode: Starting Workers + Scheduler only (Low RAM)..."
    # No Web Server, No Node, No Nginx
    bench schedule &
    exec bench worker
    ;;
  *)
    echo "⚠️ Unknown MODE: $MODE. Falling back to exec $@"
    exec "$@"
    ;;
  esac
}

# RUN LOGIC
if [ "$1" = "bench" ] && [ "$2" = "start" ]; then
  setup_site
  start_services
fi

exec "$@"
