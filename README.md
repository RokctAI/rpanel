# RPanel - Professional Web Hosting Control Panel

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Frappe Framework](https://img.shields.io/badge/Frappe-v15-orange)](https://frappeframework.com)
[![Latest Version](https://img.shields.io/github/v/release/rokctAI/rpanel?label=Stable%20Version)](https://github.com/rokctAI/rpanel/releases)
[![Build Status](https://github.com/rokctAI/rpanel/actions/workflows/auto_release.yml/badge.svg)](https://github.com/rokctAI/rpanel/actions)


**RPanel** is a powerful, open-source web hosting control panel built on the Frappe Framework (v15). It is designed to be a complete alternative to cPanel/Plesk, offering a modern UI for managing websites, databases, emails, and servers.

RPanel works by orchestrating standard open-source technologies (Nginx, PostgreSQL, MariaDB, Exim, etc.) through a beautiful, easy-to-use interface. It can manage the server it's installed on (Local Mode) or manage multiple remote servers via SSH (Cluster Mode).

## 🚀 Key Features

### 🌐 Website Management
- One-click website provisioning
- WordPress auto-installation
- PHP version management (8.3, 8.2, 8.1, 7.4)
- Nginx configuration automation
- Standard directory structure

### 🔒 SSL & Security
- Automatic Let's Encrypt SSL certificates
- SSL renewal automation
- Firewall management (UFW)
- Fail2Ban integration
- Malware scanning (ClamAV)
- Security audit logs

### 📧 Email Management
- Email account creation
- SMTP/IMAP configuration
- Roundcube webmail integration
- Email forwarding & aliases

### 💾 Database Management
- **PostgreSQL First**: Native PostgreSQL support as the core engine
- **MariaDB/MySQL**: Full compatibility for legacy sites and opt-in selection
- **WordPress Bridge**: Automated [PG4WP](https://github.com/PostgreSQL-For-Wordpress/postgresql-for-wordpress) installation for WP on PostgreSQL
- phpMyAdmin & pgAdmin integration ready
- Database user management with automatic secure credentials

### 📁 File Management
- Web-based file browser
- Upload/download files
- File editing
- Directory management
- Permission management

### 🔄 Backups & Recovery
- Automated backups (full/database/files)
- Cloud storage integration (S3, Google Drive, Dropbox)
- One-click restore
- Backup scheduling

### ⚙️ Automation
- Cron job management
- Scheduled tasks
- SSL auto-renewal
- Backup automation
- Health monitoring

### 🖥️ Multi-Server Management
- Server groups
- Load balancing
- Remote server provisioning
- SSH-based deployment
- Resource monitoring

### 🎨 White-Label Branding
- Custom logos
- Brand colors
- Client portals
- Custom domains

### 🛡️ Enterprise Compliance Readiness
RPanel is built to help you meet strict industry standards. While the software itself cannot be "certified" (only your organization can), RPanel provides the specific technical controls required for:

- **SOC 2 Compliance:**
  - **Access Control (CC6.1):** Native Two-Factor Authentication (2FA) enforcement for admins.
  - **Data Protection (CC6.7):** GPG-encrypted backups (4096-bit RSA) ensure data confidentiality at rest.

- **PCI-DSS Compliance:**
  - **WAF (Req 6.6):** Integrated ModSecurity Web Application Firewall with OWASP Core Rule Set.
  - **Vulnerability Management (Req 11.2):** Automated daily scanning for WordPress core, plugins, and malware.

- **GDPR Compliance:**
  - **Data Encryption (Art. 32):** Strong encryption for backups and SSL automation for data in transit.

### 💻 System Requirements

RPanel is a modern, feature-rich control panel. To run the full stack (Frappe, PostgreSQL, MariaDB, Redis, Nginx, Exim, ClamAV), you need a server with sufficient resources.

| Resource | Minimum | Recommended |
| :--- | :--- | :--- |
| **OS** | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| **RAM** | 4 GB | 8 GB+ |
| **CPU** | 2 Cores | 4 Cores+ |
| **Disk** | 40 GB SSD | 80 GB NVMe |

> [!WARNING]
> **ClamAV Memory Usage:** The antivirus scanner (ClamAV) alone requires ~3GB of RAM. If you have less than 8GB RAM, we recommend disabling ClamAV after installation to prevent OOM crashes.

## 💿 Installation

RPanel can be installed in two ways: as a standalone control panel on a fresh server, or as an app on an existing Frappe Bench.

### Option 1: Standalone Installation (Recommended for Fresh Servers)

This is the "Boss Mode" installation. It sets up everything from scratch on a fresh Ubuntu 22.04 or Debian 11/12 server.

**What it installs:**
- Node.js 24 & Python 3.14 (Latest Standards)
- Dual-Stack Databases (PostgreSQL + MariaDB)
- Frappe Bench & Framework (v15)
- RPanel App v1.2.0+
- Production-Ready Nginx & Supervisor configuration

**Run this command as root:**

```bash
wget https://raw.githubusercontent.com/RokctAI/rpanel/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

### Option 2: Install on Existing Bench

If you already have a Frappe Bench (v15) running, you can simply add RPanel as an app.

```bash
# 1. Get the app
cd ~/frappe-bench/apps
bench get-app https://github.com/RokctAI/rpanel.git

# 2. Install on your site
bench --site [your-site.com] install-app rpanel

# 3. Run migrations
bench --site [your-site.com] migrate
```

### Option 3: Production Install (Stable Release)

For production environments, install the latest stable release instead of the development branch:

```bash
# 1. Get latest release tag
LATEST_VERSION=$(curl -s https://api.github.com/repos/RokctAI/rpanel/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')

# 2. Install using bench
cd ~/frappe-bench
bench get-app https://github.com/RokctAI/rpanel.git --branch $LATEST_VERSION

# 3. Install on your site
bench --site [your-site.com] install-app rpanel
bench --site [your-site.com] migrate
```

**Benefits of using stable releases:**
- ✅ Tested and production-ready code
- ✅ Predictable behavior
- ✅ Easy rollback to previous versions

## ⚡ Quick Start

1. **Configure Settings:**
   - Go to: Hosting > Hosting Settings
   - Set web root path (default: `/var/www`)
   - Configure default PHP version

2. **Add a Server:**
   - Go to: Hosting > Hosting Server > New
   - Enter server details and SSH credentials
   - Click "Provision Server" to auto-install required software

3. **Create a Website:**
   - Go to: Hosting > Hosted Website > New
   - Enter domain name
   - Select server
   - Choose PHP version
   - Save to provision

4. **Enable SSL:**
   - Open the website
   - Click "Enable SSL"
   - Certificate is automatically generated

## ⚙️ Configuration

### Hosting Settings

```python
# Access via: Hosting > Hosting Settings

web_root_path = "/var/www"
default_php_version = "8.2"
enable_auto_ssl = True
enable_auto_backups = True
backup_retention_days = 30
```

### Server Provisioning

RPanel can automatically install required software on remote servers:
- Nginx
- MariaDB
- PHP (multiple versions)
- Certbot
- phpMyAdmin
- Roundcube
- ClamAV
- Fail2Ban
- UFW

## 🔌 API Usage

### Create Website Programmatically

```python
import frappe

website = frappe.get_doc({
    'doctype': 'Hosted Website',
    'domain': 'example.com',
    'server': 'Production Server 1',
    'php_version': '8.2',
    'site_type': 'CMS',
    'cms_type': 'WordPress'
})
website.insert()
```

### Enable SSL

```python
website = frappe.get_doc('Hosted Website', 'example.com')
website.enable_ssl()
```

### Create Backup

```python
backup = frappe.get_doc({
    'doctype': 'Site Backup',
    'website': 'example.com',
    'backup_type': 'Full',
    'storage_type': 'S3'
})
backup.insert()
backup.create_backup()
```

## 🏗️ Architecture

```
RPanel
├── Hosting Module
│   ├── Doctypes
│   │   ├── Hosted Website
│   │   ├── Hosting Server
│   │   ├── Hosting Client
│   │   ├── Site Backup
│   │   └── Cron Job
│   ├── Utilities
│   │   ├── SSL Manager
│   │   ├── Database Manager
│   │   ├── Email Manager
│   │   └── File Manager
│   └── Reports
│       ├── SSL Expiry Report
│       └── Website Status Report
└── Public Assets
    ├── JavaScript
    └── Templates
```

## 🤝 Contributing

We welcome contributions! RPanel is MIT Licensed and open source.

1.  Fork the repository
2.  Create a feature branch (`git checkout -b feature/amazing-feature`)
3.  Commit your changes (`git commit -m 'Add amazing feature'`)
4.  Push to the branch (`git push origin feature/amazing-feature`)
5.  Open a Pull Request

## 👥 Credits

**Author:** [Rokct Holdings](https://rokct.ai)

**Lead Developer:** [Rendani Sinyage](https://github.com/RendaniSinyage)

**Community Contributions:**
Our release notes are automatically powered by the `universal-release` workflow, capturing Authors and Reviewers from every merged Pull Request to ensure proper attribution.
- [Nurudin Ahmed](https://github.com/nurudinso)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## 🔌 Integration Guide

Building a Billing System or Control Plane? Check out our **[Integration Examples](integration_examples/README.md)** for code snippets on:
- Auto-installing RPanel
- Syncing Quotas & Plans
- Automating Provisioning

---

**RPanel** - Hosting made simple, powerful, and open.

