# RPanel Dependencies

This file serves as the **single source of truth** for all RPanel system dependencies.

## Structure

```json
{
  "system_dependencies": {
    "package-name": {
      "check": "command to check if installed",
      "install": "command to install the package",
      "description": "what this package does"
    }
  },
  "core_dependencies": {
    // Core Frappe/RPanel dependencies (Python, Redis, MariaDB, Node.js)
  }
}
```

## Usage

All installation scripts read from this file:

- `rpanel/install.py` - Python install hook for `bench install-app`
- `scripts/provision_localhost.sh` - Localhost provisioning script
- `install.sh` - Fresh VPS installer
- `rpanel/hosting/server_provisioner.py` - Remote server provisioning

## Adding a New Dependency

1. Add entry to `dependencies.json`
2. All scripts will automatically pick it up
3. No need to update multiple files

## Dependency Categories

### System Dependencies (Hosting Services)
- Web servers (nginx)
- Email (exim4, dovecot)
- SSL (certbot)
- PHP versions (8.1, 8.2, 8.3)
- Management tools (composer, wp-cli, phpmyadmin, roundcube)
- Security (clamav, fail2ban, ufw)

### Core Dependencies (Frappe Requirements)
- Python 3
- Redis
- MariaDB
- Node.js
- Yarn
