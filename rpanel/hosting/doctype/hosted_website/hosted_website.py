# Copyright (c) 2025, ROKCT Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import os
import subprocess
import re
from rpanel.hosting.utils import run_certbot, update_exim_config
from rpanel.hosting.mysql_utils import run_mysql_command
from rpanel.hosting.system_user_manager import SystemUserManager
from rpanel.hosting.php_fpm_manager import PHPFPMManager
from rpanel.hosting.postgres_utils import create_pg_database
from rpanel.hosting.service_intelligence import ServiceIntelligence


class HostedWebsite(Document):
    def validate(self):  # noqa: C901
        # 0. Check client quota (before creating new site)
        if self.is_new():
            self.check_client_quota()

        # 0b. Default DB Engine
        if not self.db_engine:
            self.db_engine = "PostgreSQL"

        # 1. Strict Domain Validation (Security)
        # Allow lowercase, numbers, dots, hyphens. No spaces, no semicolons.
        if not re.match(r'^[a-z0-9.-]+$', self.domain):
            frappe.throw("Invalid Domain Name. Only lowercase alphanumeric characters, dots, and hyphens are allowed.")

        # 2. Set system user (default to domain without dots for username)
        if not self.system_user:
            # Create safe username from domain (remove dots, limit length)
            safe_user = re.sub(r'[^a-zA-Z0-9]', '', self.domain.split('.')[0])[:16]
            self.system_user = safe_user

        # 3. Set Standard path: /var/www/{user}/data/www/{domain}
        if not self.site_path:
            self.site_path = f"/var/www/{self.system_user}/data/www/{self.domain}"

        # Validate DB Name and User to prevent SQL Injection
        if self.site_type == "CMS":
            if not self.db_name:
                # Auto-generate safe name
                safe_domain = re.sub(r'[^a-zA-Z0-9]', '_', self.domain)
                self.db_name = safe_domain[:16]

            if not self.db_user:
                self.db_user = self.db_name

            # Strict Validation
            if not re.match(r'^[a-zA-Z0-9_]+$', self.db_name):
                frappe.throw("Database Name can only contain alphanumeric characters and underscores.")
            if not re.match(r'^[a-zA-Z0-9_]+$', self.db_user):
                frappe.throw("Database User can only contain alphanumeric characters and underscores.")

    def check_client_quota(self):
        """Check if client has exceeded their website quota"""
        if not self.client:
            return  # No client assigned, skip quota check

        # Get client document
        client = frappe.get_doc("Hosting Client", self.client)

        # Count existing websites for this client
        existing_count = frappe.db.count("Hosted Website", {
            "client": self.client,
            "name": ["!=", self.name]  # Exclude current site if updating
        })

        # Check against limit
        if hasattr(client, 'max_websites') and client.max_websites:
            if existing_count >= client.max_websites:
                frappe.throw(
                    f"Website quota exceeded. Your plan allows {client.max_websites} website(s). "
                    f"You currently have {existing_count} website(s). "
                    f"Please upgrade your plan to create more websites.",
                    title="Quota Exceeded"
                )

    def after_insert(self):
        if self.status == "Active":
             self.provision_site()

    def on_update(self):
        if self.status == "Active":
            # 1. Provisioning Logic (if newly active or generic update)
            if self.has_value_changed("status"):
                self.provision_site()

            # 2. Nginx Updates
            if self.has_value_changed("php_version") or self.has_value_changed("site_type"):
                self.update_nginx_config()

            # 3. Email Updates
            if self.has_value_changed("email_accounts"):
                self.update_email_config()

            # 4. CMS/Database Installation Logic (State Change: Manual -> CMS)
            if self.site_type == "CMS" and self.cms_type == "WordPress":
                # Check if we just switched to CMS or if DB details are missing/changed
                # Robustness: Just try to run setup. It checks if exists internally.
                if self.has_value_changed("site_type") or self.has_value_changed("cms_type") or self.has_value_changed("db_engine"):
                    self.setup_database()
                    self.install_wordpress()

        elif self.status == "Suspended":
            if self.has_value_changed("status"):
                self.suspend_site()

    def on_trash(self):
        self.deprovision_site()

    @frappe.whitelist()
    def provision_site(self):  # noqa: C901
        """Creates directory and basic config"""
        if self.status != "Active":
            return

        try:
            # 0. Create/verify system user and increment reference count
            user_mgr = SystemUserManager()
            if not user_mgr.user_exists(self.system_user):
                user_mgr.create_user(self.system_user)
                frappe.msgprint(f"Created Linux user: {self.system_user}")
            user_mgr.increment_user_reference(self.system_user, self.domain)

            # 0b. Create PHP-FPM pool if using PHP-FPM mode
            if self.php_mode == "PHP-FPM":
                php_mgr = PHPFPMManager(self.php_version)
                socket_path = php_mgr.create_pool(
                    domain=self.domain,
                    system_user=self.system_user,
                    max_children=5
                )
                # Store socket path for nginx config
                self.php_fpm_socket = socket_path

            # 1. Create Directory
            if not os.path.exists(self.site_path):
                subprocess.run(["sudo", "mkdir", "-p", self.site_path], check=True)
                # Create a basic index.html if empty
                index_file = os.path.join(self.site_path, "index.html")
                if not os.path.exists(index_file):
                    with open("temp_index.html", "w") as f:
                        f.write(f"<h1>Welcome to {self.domain}</h1><p>Hosted by ROKCT</p>")
                    subprocess.run(["sudo", "mv", "temp_index.html", index_file], check=True)

                # Set permissions to system user
                subprocess.run(["sudo", "chown", "-R", f"{self.system_user}:www-data", self.site_path], check=True)
                subprocess.run(["sudo", "chmod", "-R", "755", self.site_path], check=True)

            # 2. Nginx Config
            self.update_nginx_config()

            # 3. Database (if CMS)
            if self.site_type == "CMS" and self.cms_type == "WordPress":
                self.setup_database()
                self.install_wordpress()

            # 3b. Frappe Tenant Provisioning
            if self.site_type == "Frappe Tenant":
                self.provision_frappe_tenant()

            # 4. Emails
            self.update_email_config()

            # 5. Issue SSL
            # Check if SSL is already valid
            if not self.ssl_status or self.ssl_status != "Active":
                 self.issue_ssl()

            frappe.msgprint(f"Site {self.domain} provisioned successfully.")

        except Exception as e:
            frappe.log_error(f"Provisioning failed for {self.domain}: {e}")
            frappe.msgprint(f"Provisioning Warning: {e}")

    def provision_frappe_tenant(self):
        """Provisions a new Frappe site and installs selected apps"""
        frappe.msgprint("Provisioning Frappe Tenant...")
        try:
            # 1. Create Site
            # We use the current bench to create a new site
            # Note: This requires the process to have permissions to run bench commands
            # and the db root password must be configured in common_site_config.json or passed somehow.
            # For security, we assume common_site_config.json has the root credentials or we use a specific admin user.

            # Check if site exists
            if os.path.exists(os.path.join(frappe.utils.get_bench_path(), "sites", self.domain)):
                frappe.msgprint("Site directory already exists. Skipping creation.")
            else:
                # Create site
                # We need to pass the admin password.
                # Ideally, we should generate a random one and set it.
                admin_password = self.db_password or frappe.generate_hash(length=12)
                self.db_password = admin_password
                self.save()

                cmd = ["bench", "new-site", self.domain, "--admin-password", admin_password, "--no-mariadb-socket"]
                # If db_name is set, use it? bench new-site generates its own usually, but we can try to force if needed.
                # Standard bench new-site uses the site name (domain) as db name usually (sanitized).

                subprocess.run(cmd, check=True, cwd=frappe.utils.get_bench_path())

            # 2. Install Apps
            if self.apps_to_install:
                apps = [app.app_name for app in self.apps_to_install]
                cmd = ["bench", "--site", self.domain, "install-app"] + apps
                subprocess.run(cmd, check=True, cwd=frappe.utils.get_bench_path())

            # 3. Set App Role (Tenant)
            # We manually edit the site_config.json of the new site
            site_config_path = os.path.join(frappe.utils.get_bench_path(), "sites", self.domain, "site_config.json")
            if os.path.exists(site_config_path):
                import json
                with open(site_config_path, "r") as f:
                    config = json.load(f)

                config["app_role"] = "tenant"

                with open(site_config_path, "w") as f:
                    json.dump(config, f, indent=4)

            frappe.msgprint(f"Frappe Tenant {self.domain} created successfully.")

        except subprocess.CalledProcessError as e:
            frappe.log_error(f"Frappe Tenant Creation Failed: {e}")
            frappe.throw("Failed to create Frappe Tenant. Check error logs.")

    def install_wordpress(self):
        if os.path.exists(os.path.join(self.site_path, "wp-config.php")):
            return  # Already installed

        frappe.msgprint("Installing WordPress...")
        try:
            # Use WP-CLI to download WordPress (uses version installed on server)
            # This gives admins control over WP version via Service Version management

            # 1. Download WordPress using WP-CLI
            subprocess.run([
                "sudo", "-u", "www-data", "wp", "core", "download",
                f"--path={self.site_path}",
                "--allow-root"
            ], check=True)

            # 2. Generate wp-config.php
            self.generate_wp_config()

            # 2b. Setup PostgreSQL bridge (if needed)
            if self.db_engine == "PostgreSQL":
                self.setup_wordpress_postgres_bridge()

            # 3. Permissions
            subprocess.run(["sudo", "chown", "-R", "www-data:www-data", self.site_path], check=True)

            frappe.msgprint("WordPress installed successfully")

        except subprocess.CalledProcessError as e:
            frappe.log_error(f"WP Install Failed: {e}")
            frappe.throw("WordPress Installation Failed. Please check if WP-CLI is installed on the server.")

    def generate_wp_config(self):
        import requests
        try:
            salts = requests.get('https://api.wordpress.org/secret-key/1.1/salt/').text
        except requests.RequestException:
            salts = ""
            # Log warning

        config = f"""<?php
define( 'DB_NAME', '{self.db_name}' );
define( 'DB_USER', '{self.db_user}' );
define( 'DB_PASSWORD', '{self.db_password}' );
define( 'DB_HOST', 'localhost' );
define( 'DB_CHARSET', 'utf8' );
define( 'DB_COLLATE', '' );

{salts}

$table_prefix = 'wp_';

define( 'WP_DEBUG', false );

if ( ! defined( 'ABSPATH' ) ) {{
    define( 'ABSPATH', __DIR__ . '/' );
}}

require_once ABSPATH . 'wp-settings.php';
"""
        # Write to temp file then move
        temp_config = f"/tmp/wp-config-{self.name}.php"
        with open(temp_config, "w") as f:
            f.write(config)

        subprocess.run(["sudo", "mv", temp_config, os.path.join(self.site_path, "wp-config.php")], check=True)

    def setup_wordpress_postgres_bridge(self):
        """Install PG4WP bridge for WordPress on PostgreSQL"""
        frappe.msgprint("Setting up PostgreSQL bridge for WordPress...")
        try:
            # 1. Download PG4WP
            # We can use a pre-installed version on the server or download it.
            # For now, let's assume we maintain a cached copy in /var/lib/rpanel/plugins/
            bridge_source = "/var/lib/rpanel/plugins/pg4wp"

            # Cleanup if old repo exists but is empty (archived repo issues)
            if os.path.exists(bridge_source) and not os.listdir(bridge_source):
                subprocess.run(["sudo", "rm", "-rf", bridge_source], check=True)

            if not os.path.exists(bridge_source):
                # Download if missing
                subprocess.run([
                    "sudo", "git", "clone", "https://github.com/PostgreSQL-For-Wordpress/postgresql-for-wordpress.git",
                    bridge_source
                ], check=True)

            # 2. Copy db.php to wp-content/
            wp_content = os.path.join(self.site_path, "wp-content")
            subprocess.run(["sudo", "mkdir", "-p", wp_content], check=True)
            subprocess.run([
                "sudo", "cp", os.path.join(bridge_source, "pg4wp/db.php"),
                os.path.join(wp_content, "db.php")
            ], check=True)

            # 3. Copy pg4wp directory to wp-content/
            subprocess.run([
                "sudo", "cp", "-r", os.path.join(bridge_source, "pg4wp"),
                wp_content
            ], check=True)

            frappe.msgprint("PostgreSQL bridge configured")

        except Exception as e:
            frappe.log_error(f"WP PG Bridge Failed: {e}")
            frappe.msgprint(f"Warning: Failed to setup PG bridge. WordPress might not connect. {e}")

    def issue_ssl(self):
        # Webroot must exist first
        if not os.path.exists(self.site_path):
             frappe.throw("Site directory does not exist. Cannot issue SSL.")

        success, msg = run_certbot(self.domain, self.site_path)
        if success:
            self.db_set('ssl_status', 'Active')
            self.db_set('ssl_issuer', "Let's Encrypt")
            # Update Nginx to use SSL
            self.update_nginx_config(ssl=True)
            frappe.msgprint(msg)
        else:
            self.db_set('ssl_status', 'Failed')
            frappe.msgprint(f"SSL Issuance Failed: {msg}")

    def update_nginx_config(self, ssl=False):
        """Generates and reloads Nginx config"""
        config_path = f"/etc/nginx/conf.d/{self.domain}.conf"

        # Determine which PHP-FPM socket to use
        # Use dedicated socket if available (for isolated pools), otherwise default
        if hasattr(self, 'php_fpm_socket') and self.php_fpm_socket:
            php_socket = self.php_fpm_socket
        else:
            # Fallback to default socket (discovered via ServiceIntelligence)
            php_socket = ServiceIntelligence.get_php_fpm_socket(self.php_version)

        listen_block = "listen 80;"
        ssl_block = ""

        # Check if SSL certs exist to enable SSL block safely
        cert_path = f"/etc/letsencrypt/live/{self.domain}/fullchain.pem"
        key_path = f"/etc/letsencrypt/live/{self.domain}/privkey.pem"

        # We can only enable SSL if the files actually exist on disk, regardless of our 'ssl' flag intent
        # But checking existence via python requires read access to /etc/letsencrypt which we might not have without sudo.
        # So we assume if ssl=True (which we set after success) it's good.

        if ssl or (self.ssl_status == 'Active'):
            listen_block = f"""
    listen 80;
    listen 443 ssl;
    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};
"""
            # Force redirect to HTTPS
            ssl_block = """
    if ($scheme != "https") {{
        return 301 https://$host$request_uri;
    }}
"""

        config_content = r"""
server {{
    {listen_block}
    server_name {domain} www.{domain};
    root {site_path};
    index index.php index.html index.htm;

    {ssl_block}

    location / {{
        try_files $uri $uri/ /index.php?$args;
    }}

    location ~ \.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:{php_socket};
    }}

    # Deny access to .htaccess
    location ~ /\.ht {{
        deny all;
    }}

    # Webmail alias (Roundcube)
    location /webmail {{
        alias /var/www/roundcube;
        index index.php;
        try_files $uri $uri/ @roundcube;

        location ~ \.php$ {{
            include snippets/fastcgi-php.conf;
            fastcgi_pass unix:{php_socket};
            fastcgi_param SCRIPT_FILENAME $request_filename;
        }}
    }}

    location @roundcube {{
        rewrite /webmail/(.*) /webmail/index.php?_url=/$1;
    }}
}}
""".format(listen_block=listen_block, domain=self.domain, site_path=self.site_path, ssl_block=ssl_block, php_socket=php_socket)
        # Write to temp then move
        # Use /tmp/ to avoid polluting app dir
        temp_conf = f"/tmp/nginx_{self.name}.conf"
        with open(temp_conf, "w") as f:
            f.write(config_content)

        try:
            subprocess.run(["sudo", "mv", temp_conf, config_path], check=True)
            subprocess.run(["sudo", "systemctl", "reload", "nginx"], check=True)
        except subprocess.CalledProcessError as e:
            frappe.log_error(f"Nginx reload failed: {e}")
            frappe.throw("Failed to reload Nginx configuration.")

    def update_email_config(self):
        """Updates Exim4/Dovecot files based on email accounts"""
        accounts = []
        for row in self.email_accounts:
             accounts.append({
                 'user': row.email_user,
                 'password': row.get_password('password'),  # Safe retrieval
                 'forward_to': row.forward_to
             })

        success, msg = update_exim_config(self.domain, accounts)
        if not success:
             frappe.msgprint(f"Email Update Warning: {msg}")

    def setup_database(self):
        """Creates database and user based on engine"""
        # Double check validation
        if not re.match(r'^[a-zA-Z0-9_]+$', self.db_name) or not re.match(r'^[a-zA-Z0-9_]+$', self.db_user):
             frappe.throw("Invalid Database Name or User")

        if not self.db_password:
            self.db_password = frappe.generate_hash(length=12)
            self.db_update()

        try:
            if self.db_engine == "MariaDB":
                self.setup_mariadb()
            else:
                self.setup_postgresql()

        except Exception as e:
             frappe.log_error(f"Database setup failed: {e}")
             frappe.throw(f"Failed to setup {self.db_engine} database: {e}")

    def setup_mariadb(self):
        """Specific MariaDB setup logic"""
        # Create DB
        subprocess.run(["sudo", "mysql", "-e", f"CREATE DATABASE IF NOT EXISTS `{self.db_name}`;"], check=True)

        # Create User
        run_mysql_command(
            sql=f"CREATE USER IF NOT EXISTS '{self.db_user}'@'localhost' IDENTIFIED BY '{self.db_password}';",
            as_sudo=True
        )

        # Grant Privileges
        run_mysql_command(
            sql=f"GRANT ALL PRIVILEGES ON `{self.db_name}`.* TO '{self.db_user}'@'localhost';",
            as_sudo=True
        )
        run_mysql_command(sql="FLUSH PRIVILEGES;", as_sudo=True)

    def setup_postgresql(self):
        """Specific PostgreSQL setup logic"""
        create_pg_database(self.db_name, self.db_user, self.db_password)

    def deprovision_site(self):
        """Removes config and (optionally) data"""
        try:
            # Remove PHP-FPM pool if exists
            if hasattr(self, 'php_fpm_socket') and self.php_fpm_socket:
                php_mgr = PHPFPMManager(self.php_version)
                php_mgr.delete_pool(self.domain)

            # Decrement user reference count and delete if no other sites use it
            user_mgr = SystemUserManager()
            user_mgr.decrement_user_reference(self.system_user, self.domain)

            remaining_sites = user_mgr.get_user_reference_count(self.system_user)
            if remaining_sites == 0:
                # No other sites use this user, safe to delete
                frappe.msgprint(f"No other sites use {self.system_user}, removing user...")
                user_mgr.delete_user(self.system_user)
            else:
                frappe.msgprint(f"User {self.system_user} still used by {remaining_sites} other site(s), preserving...")

            # Remove Nginx config
            config_path = f"/etc/nginx/conf.d/{self.domain}.conf"
            if os.path.exists(config_path):
                subprocess.run(["sudo", "rm", config_path], check=True)
                subprocess.run(["sudo", "systemctl", "reload", "nginx"], check=True)

            # Remove Directory (Archive it instead of delete?)
            # For now, let's rename it to .deleted
            if os.path.exists(self.site_path):
                archive_path = f"{self.site_path}_deleted_{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}"
                subprocess.run(["sudo", "mv", self.site_path, archive_path], check=True)

        except Exception as e:
             frappe.log_error(f"Deprovisioning failed: {e}")

    def suspend_site(self):
        """Updates Nginx to show suspension page"""
        try:
            # Ensure suspension page exists in a global location
            suspension_page = "/var/www/html/suspended.html"
            if not os.path.exists(suspension_page):
                # Copy from app templates if not exists (requires finding app path)
                # For now, we'll write a simple one if missing
                with open("/tmp/suspended.html", "w") as f:
                    f.write("<h1>Account Suspended</h1>")
                subprocess.run(["sudo", "mv", "/tmp/suspended.html", suspension_page], check=True)

            config_path = f"/etc/nginx/conf.d/{self.domain}.conf"

            config_content = f"""
server {{
    listen 80;
    server_name {self.domain} www.{self.domain};
    root /var/www/html;
    index suspended.html;

    location / {{
        try_files /suspended.html =503;
    }}

    error_page 503 /suspended.html;
    location = /suspended.html {{
        internal;
    }}
}}
"""
            temp_conf = f"/tmp/nginx_suspend_{self.name}.conf"
            with open(temp_conf, "w") as f:
                f.write(config_content)

            subprocess.run(["sudo", "mv", temp_conf, config_path], check=True)
            subprocess.run(["sudo", "systemctl", "reload", "nginx"], check=True)
            frappe.msgprint(f"Site {self.domain} suspended.")

        except Exception as e:
            frappe.log_error(f"Suspension failed: {e}")
            frappe.msgprint(f"Suspension failed: {e}")
