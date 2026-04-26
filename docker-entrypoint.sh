#!/bin/bash
set -e

# --- Environment Injection ---
# Allow dynamic overrides for portable spoke containers
if [ -n "$DB_HOST" ]; then bench set-config -g db_host "$DB_HOST"; fi
if [ -n "$REDIS_CACHE" ]; then bench set-config -g redis_cache "$REDIS_CACHE"; fi
if [ -n "$REDIS_QUEUE" ]; then bench set-config -g redis_queue "$REDIS_QUEUE"; fi
if [ -n "$REDIS_SOCKETIO" ]; then bench set-config -g redis_socketio "$REDIS_SOCKETIO"; fi

# Function to setup the site based on MODE
setup_site() {
  # The baked site in the image is usually 'rpanel.local'
  BAKED_SITE="rpanel.local"
  if [ ! -d "sites/$BAKED_SITE" ]; then BAKED_SITE="platform.rokct.ai"; fi

  if [ ! -d "sites/$SITE_NAME" ]; then
    echo "🔥 Site '$SITE_NAME' not found in volume."

    if [ -d "sites/$BAKED_SITE" ] && [ "$SITE_NAME" != "$BAKED_SITE" ]; then
      echo "🔄 Found baked site '$BAKED_SITE'. Renaming to '$SITE_NAME'..."
      bench rename-site "$BAKED_SITE" "$SITE_NAME" || {
        echo "⚠️ Rename failed, moving directory manually..."
        mv "sites/$BAKED_SITE" "sites/$SITE_NAME"
      }
    else
      echo "✨ Initializing new site '$SITE_NAME'..."
      # 1. Database Connection Check (Retry logic for portable spokes)
      if [ -n "$DB_HOST" ]; then
        echo "⏳ Waiting for Database at $DB_HOST..."
        until nc -z "$DB_HOST" "${DB_PORT:-5432}"; do sleep 1; done
      fi

      # 2. Base Installation / Restoration
      # Base apps are always installed, INSTALL_APPS contains additions from the Hub
      BASE_APPS="rcore brain"
      if [ "$MODE" = "full" ]; then BASE_APPS="rpanel rcore paas control brain"; fi

      # Merge base apps with additional apps, ensuring no duplicates
      FINAL_APPS=$(echo "$BASE_APPS $INSTALL_APPS" | tr ' ' '\n' | sort -u | tr '\n' ' ' | xargs)

      if [ -f "apps/seed_data/seed.sql.gz" ]; then
        echo "✨ Restoring from Golden Seed (Apps: $FINAL_APPS)..."
        bench new-site "$SITE_NAME" \
          --source-sql "apps/seed_data/seed.sql.gz" \
          --admin-password "${ADMIN_PASSWORD:-admin}" \
          --db-root-password "${DB_ROOT_PASSWORD:-admin}" \
          --install-app "$FINAL_APPS" \
          --force
      else
        echo "⚠️ No Golden Seed found. Performing clean install (Apps: $FINAL_APPS)..."
        bench new-site "$SITE_NAME" \
          --admin-password "${ADMIN_PASSWORD:-admin}" \
          --db-root-password "${DB_ROOT_PASSWORD:-admin}" \
          --install-app "$FINAL_APPS"
      fi
    fi

    # Ensure app_role is set
    bench --site "$SITE_NAME" set-config app_role "${APP_ROLE:-$MODE}"
    bench use "$SITE_NAME"
  else
    echo "✅ Site '$SITE_NAME' already exists in volume."
    # Ensure any updated ENV variables are applied to the existing site
    if [ -n "$DB_HOST" ]; then bench --site "$SITE_NAME" set-config db_host "$DB_HOST"; fi
  fi

  # --- ROK persistence ---
  mkdir -p "sites/$SITE_NAME/private/rok"
  if [ ! -L "/home/frappe/.rok" ]; then
    rm -rf "/home/frappe/.rok" || true
    ln -sfn "$PWD/sites/$SITE_NAME/private/rok" "/home/frappe/.rok"
  fi
}

# Function to start services
start_services() {
  case "$MODE" in
  "full")
    echo "💻 Full Mode (Control Hub): Starting Web + Mail + Bench..."
    if [ "$(id -u)" = "0" ]; then
      service exim4 start || true
      nginx -g 'daemon off;' &
      exec su-exec frappe bench start
    else
      exec bench start
    fi
    ;;
  "api")
    echo "🔌 API Mode (Headless Spoke): Starting Gunicorn + Workers..."
    bench worker &
    bench schedule &
    exec bench serve --port 8000
    ;;
  "iot")
    echo "🔋 IoT Mode (Edge Spoke): Starting Workers + Scheduler only..."
    bench schedule &
    exec bench worker
    ;;
  *)
    echo "⚠️ Unknown MODE: $MODE. Executing: $@"
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
