#!/bin/bash
set -e

# --- Environment Injection is now handled inside setup_site to ensure bench context exists ---

# Function to setup the site based on MODE
setup_site() {
  # 1. Robust Site Discovery (Req 1)
  # Probe for any initialized site (containing site_config.json)
  BAKED_SITE=$(ls sites/*/site_config.json 2>/dev/null | head -1 | cut -d/ -f2)

  if [ ! -d "sites/$SITE_NAME" ]; then
    echo "🔥 Target site '$SITE_NAME' not found in volume."

    # If we have a baked/existing site, RENAME it to the target site name
    if [ -n "$BAKED_SITE" ] && [ "$SITE_NAME" != "$BAKED_SITE" ]; then
      echo "🔄 Found initialized site '$BAKED_SITE'. Renaming to '$SITE_NAME'..."
      # Note: bench rename-site is non-standard. If it fails, we fall back to mv.
      bench rename-site "$BAKED_SITE" "$SITE_NAME" || {
        echo "⚠️ bench rename-site failed. Performing directory move only..."
        echo "⚠️ Database references for '$BAKED_SITE' may remain; run 'bench migrate' to refresh."
        mv "sites/$BAKED_SITE" "sites/$SITE_NAME"
      }

      # Improvement 1: Install apps after rename
      if [ -n "$INSTALL_APPS" ]; then
        echo "📦 Installing additional apps for renamed site: $INSTALL_APPS"
        for app in $INSTALL_APPS; do
          bench --site "$SITE_NAME" install-app "$app" || echo "⚠️ Failed to install $app (might already be installed)"
        done
      fi
    else
      echo "✨ Initializing brand new site '$SITE_NAME'..."
      # 1. Database Connection Check (Retry logic for portable spokes)
      if [ -n "$DB_HOST" ]; then
        echo "⏳ Waiting for Database at $DB_HOST..."
        until nc -z "$DB_HOST" "${DB_PORT:-5432}"; do sleep 1; done
      fi

      # 2. Base Installation / Restoration
      BASE_APPS="rcore brain"
      if [ "$MODE" = "full" ]; then BASE_APPS="rpanel rcore paas control brain"; fi

      # Merge base apps with additional apps, ensuring no duplicates
      # Use :- to guard against unset variables (Req 5)
      FINAL_APPS=$(echo "$BASE_APPS ${INSTALL_APPS:-}" | tr ' ' '\n' | sort -u | tr '\n' ' ')

      # Use an array for flags to handle spaces and empty lists cleanly (Req 2)
      INSTALL_APP_FLAGS=()
      for app in $FINAL_APPS; do
        INSTALL_APP_FLAGS+=(--install-app "$app")
      done

      if [ -f "apps/seed_data/seed.sql.gz" ]; then
        echo "✨ Restoring from Golden Seed (Apps: $FINAL_APPS)..."
        bench new-site "$SITE_NAME" \
          --source-sql "apps/seed_data/seed.sql.gz" \
          --admin-password "${ADMIN_PASSWORD:-admin}" \
          --db-root-password "${DB_ROOT_PASSWORD:-admin}" \
          "${INSTALL_APP_FLAGS[@]}" \
          --force
      else
        echo "⚠️ No Golden Seed found. Performing clean install (Apps: $FINAL_APPS)..."
        bench new-site "$SITE_NAME" \
          --admin-password "${ADMIN_PASSWORD:-admin}" \
          --db-root-password "${DB_ROOT_PASSWORD:-admin}" \
          "${INSTALL_APP_FLAGS[@]}"
      fi
    fi

    # 3. Final configuration (Req 3: Map api -> tenant)
    # This block runs for both new-site and rename paths.
    DETERMINED_ROLE="$MODE"
    if [ "$MODE" = "api" ]; then DETERMINED_ROLE="tenant"; fi

    echo "⚙️ Finalizing configuration (Role: $DETERMINED_ROLE)..."
    bench --site "$SITE_NAME" set-config app_role "${APP_ROLE:-$DETERMINED_ROLE}"
  else
    echo "✅ Site '$SITE_NAME' already exists in volume."
    # Ensure any updated ENV variables are applied to the existing site
    if [ -n "$DB_HOST" ]; then bench --site "$SITE_NAME" set-config db_host "$DB_HOST"; fi
  fi

  # Ensure the default site is set for this container session
  bench use "$SITE_NAME"

  # --- Global Config Injection (Moved from top to ensure common_site_config.json exists) ---
  if [ -n "$DB_HOST" ]; then bench set-config -g db_host "$DB_HOST"; fi
  if [ -n "$REDIS_CACHE" ]; then bench set-config -g redis_cache "$REDIS_CACHE"; fi
  if [ -n "$REDIS_QUEUE" ]; then bench set-config -g redis_queue "$REDIS_QUEUE"; fi
  if [ -n "$REDIS_SOCKETIO" ]; then bench set-config -g redis_socketio "$REDIS_SOCKETIO"; fi

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
    WORKER_PID=$!
    bench schedule &
    SCHED_PID=$!
    # wait -n requires bash 4.3+ (Ubuntu 24.04 ships 5.2)
    bench serve --port 8000 &
    SERVE_PID=$!

    wait -n
    CODE=$?

    # Identify which process triggered the exit for better logs
    for pid in $WORKER_PID $SCHED_PID $SERVE_PID; do
      if ! kill -0 "$pid" 2>/dev/null; then
        echo "🚨 Process PID $pid has exited with code $CODE. Shutting down container..."
      fi
    done
    exit $CODE
    ;;
  "iot")
    echo "🔋 IoT Mode (Edge Spoke): Starting Workers + Scheduler only..."
    bench schedule &
    SCHED_PID=$!
    bench worker &
    WORKER_PID=$!
    # wait -n requires bash 4.3+ (Ubuntu 24.04 ships 5.2)
    wait -n
    CODE=$?

    for pid in $WORKER_PID $SCHED_PID; do
      if ! kill -0 "$pid" 2>/dev/null; then
        echo "🚨 Process PID $pid has exited with code $CODE. Shutting down container..."
      fi
    done
    exit $CODE
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
