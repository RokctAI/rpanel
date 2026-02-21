import subprocess
import os
import re


class ServiceIntelligence:
    """
    Dynamic detection of service versions and paths.
    Ensures RPanel works across different Ubuntu/Debian distributions
    without hardcoded version strings.
    """

    @staticmethod
    def get_postgresql_major_version():
        """Detect installed PostgreSQL major version"""
        try:
            # Try psql first
            result = subprocess.run(['psql', '--version'], capture_output=True, text=True, check=True)
            # Extract first number (e.g. "psql (PostgreSQL) 15.10" -> "15")
            match = re.search(r'\(PostgreSQL\)\s+([0-9]+)', result.stdout)
            if match:
                return match.group(1)
        except Exception:
            pass

        # Fallback: check /etc/postgresql directory
        try:
            if os.path.exists('/etc/postgresql'):
                versions = [d for d in os.listdir('/etc/postgresql') if d.isdigit()]
                if versions:
                    return sorted(versions, reverse=True)[0]
        except Exception:
            pass

        return "15"  # Sensible default for modern systems

    @staticmethod
    def get_installed_php_versions():
        """Get list of all installed PHP versions (e.g. ['8.3', '8.2'])"""
        versions = []
        try:
            if os.path.exists('/etc/php'):
                # Look for directories like 8.1, 8.2, 8.3 in /etc/php
                versions = [d for d in os.listdir('/etc/php')
                            if re.match(r'^[0-9]\.[0-9]$', d) and os.path.isdir(os.path.join('/etc/php', d))]
        except Exception:
            pass
        return sorted(versions, reverse=True)

    @staticmethod
    def get_default_php_version():
        """Detect the best PHP version to use as default"""
        versions = ServiceIntelligence.get_installed_php_versions()
        if versions:
            return versions[0]
        return "8.2"  # Project fallback

    @staticmethod
    def get_php_fpm_socket(version=None, user=None):
        """Get path to PHP-FPM socket"""
        ver = version or ServiceIntelligence.get_default_php_version()
        if user:
            return f"/run/php/php{ver}-fpm-{user}.sock"
        return f"/run/php/php{ver}-fpm.sock"

    @staticmethod
    def get_php_fpm_pool_dir(version=None):
        """Get PHP-FPM pool configuration directory"""
        ver = version or ServiceIntelligence.get_default_php_version()
        return f"/etc/php/{ver}/fpm/pool.d"
