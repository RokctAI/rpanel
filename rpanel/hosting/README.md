# ROKCT Hosting Module

A comprehensive web hosting control panel module for Frappe. Manage websites, SSL certificates, databases, and email accounts from a single interface.

## Features

### 🌐 Website Management
- **Multi-site hosting** - Host multiple websites on a single server
- **WordPress auto-installation** - One-click WordPress deployment
- **PHP version management** - Support for PHP 7.4, 8.1, 8.2, 8.3
- **Custom site paths** - Flexible directory structure

### 🔒 SSL & Security
- **Let's Encrypt integration** - Free SSL certificates via Certbot
- **Automatic SSL renewal** - Keep certificates up to date
- **HTTPS enforcement** - Automatic redirect to secure connections
- **SSL status tracking** - Monitor certificate expiration

### 📧 Email Management
- **Email account creation** - Manage email accounts per domain
- **Exim4 integration** - Full email server configuration
- **Email forwarding** - Forward emails to external addresses
- **Webmail access** - Roundcube webmail integration
- **Quota management** - Set mailbox size limits

### 🗄️ Database Management
- **MySQL/MariaDB support** - Automatic database creation
- **Secure credentials** - Auto-generated passwords
- **Database user management** - Granular permissions

### ⚙️ System Configuration
- **Nginx configuration** - Automatic virtual host setup
- **Service monitoring** - Check status of Nginx, MySQL, Exim4
- **System tools** - Reload services, test email, check status

## Installation

1. **Install the module** (already part of ROKCT app)
2. **Import the workspace fixture**:
   ```bash
   bench --site [your-site] import-doc hosting/fixtures/hosting_workspace.json
   ```
3. **Configure Hosting Settings**:
   - Navigate to Hosting Settings
   - Set paths for Nginx, web root, and email configuration
   - Configure SSL renewal commands

## Usage

### Creating a New Website

1. Go to **Hosting** workspace
2. Click **New Website** shortcut
3. Fill in:
   - Domain name
   - Site type (Manual or CMS)
   - PHP version
   - Status (set to Active to provision)
4. Save

The system will automatically:
- Create directory structure
- Generate Nginx configuration
- Set up database (if CMS)
- Install WordPress (if selected)
- Configure email accounts
- Issue SSL certificate

### Managing SSL Certificates

- **Issue SSL**: Click "Issue SSL Certificate" button on website form
- **Monitor expiry**: Use "SSL Expiring" shortcut in workspace
- **Renew platform SSL**: Use Hosting Settings buttons

### Email Configuration

1. Open a Hosted Website
2. Scroll to **Email Accounts** section
3. Add email accounts with:
   - Email user (e.g., "info", "support")
   - Password
   - Optional forwarding address
   - Quota in MB
4. Save to update Exim configuration

### Installing Roundcube Webmail

1. Go to **Hosting Settings**
2. Click **Install/Update Roundcube** button
3. Access webmail at `https://yourdomain.com/webmail`

## Workspace Features

The **Hosting** workspace provides:

### Quick Shortcuts
- **New Website** - Create new hosted site
- **All Websites** - View all sites
- **Active Sites** - Filter active sites
- **SSL Expiring** - Track SSL renewals
- **Settings** - System configuration

### Organized Sections
- **Website Management** - Site creation and management
- **SSL & Security** - Certificate management
- **Email Management** - Email account configuration
- **Database Management** - Database overview
- **System Configuration** - Server settings

## JavaScript Enhancements

### Hosted Website Form
- **Custom buttons**: Provision, SSL, Quick Links, Deprovision
- **Status indicators**: Visual status for SSL and site status
- **Quick actions**: Open website, WordPress admin, webmail
- **Auto-generation**: Database names from domain

### List View
- **Color indicators**: Green (Active+SSL), Blue (Active), Orange (Pending), Red (Error/Suspended)
- **Bulk actions**: Provision multiple sites at once
- **Filter shortcuts**: Quick filters for active, SSL, WordPress sites
- **Domain links**: Clickable domains with SSL indicator

### Hosting Settings
- **System status**: Check Nginx, MySQL, Exim4 status
- **Nginx reload**: Reload configuration without restart
- **Email testing**: Send test emails to verify configuration

## File Structure

```
hosting/
├── __init__.py
├── utils.py                          # Certbot and Exim utilities
├── fixtures/
│   └── hosting_workspace.json        # Workspace definition
└── doctype/
    ├── hosted_website/
    │   ├── hosted_website.json       # DocType definition
    │   ├── hosted_website.py         # Server-side logic
    │   ├── hosted_website.js         # Client-side enhancements
    │   └── hosted_website_list.js    # List view customization
    ├── hosted_email_account/
    │   ├── hosted_email_account.json # Email account child table
    │   └── hosted_email_account.py   # Email account logic
    └── hosting_settings/
        ├── hosting_settings.json     # Settings DocType
        ├── hosting_settings.py       # Settings logic
        └── hosting_settings.js       # Settings UI enhancements
```

## System Requirements

- **OS**: Linux (Ubuntu/Debian recommended)
- **Web Server**: Nginx
- **Database**: MySQL/MariaDB
- **Mail Server**: Exim4
- **SSL**: Certbot (Let's Encrypt)
- **PHP**: PHP-FPM (multiple versions)
- **Permissions**: sudo access for system commands

## Security Considerations

- **Input validation**: Strict validation for domain names, database names
- **SQL injection prevention**: Parameterized queries and validation
- **File permissions**: Proper ownership (www-data) and permissions (755)
- **Password security**: Auto-generated secure passwords
- **SSL enforcement**: HTTPS redirect for SSL-enabled sites

## Troubleshooting

### Site not accessible
- Check Nginx configuration: `sudo nginx -t`
- Verify site directory exists and has correct permissions
- Check Nginx error logs: `sudo tail -f /var/log/nginx/error.log`

### SSL certificate failed
- Ensure domain points to server IP
- Check Certbot logs: `sudo tail -f /var/log/letsencrypt/letsencrypt.log`
- Verify webroot path is correct
- Ensure port 80 is accessible

### Email not working
- Check Exim status: `sudo systemctl status exim4`
- Verify email configuration in `/etc/exim4/`
- Test email from command line: `echo "test" | mail -s "test" user@domain.com`

### WordPress installation failed
- Check PHP-FPM is running: `sudo systemctl status php8.2-fpm`
- Verify database credentials
- Check site directory permissions
- Review error logs in Frappe

## API Methods

### Hosted Website
- `provision_site()` - Provision/re-provision website
- `issue_ssl()` - Request SSL certificate
- `install_wordpress()` - Install WordPress
- `setup_database()` - Create database and user
- `update_nginx_config()` - Regenerate Nginx config
- `update_email_config()` - Update Exim configuration
- `deprovision_site()` - Remove site configuration

### Hosting Settings
- `renew_platform_ssl()` - Renew platform SSL
- `renew_wildcard_ssl()` - Renew wildcard SSL
- `install_roundcube()` - Install Roundcube webmail
- `get_system_status()` - Check service status
- `reload_nginx()` - Reload Nginx
- `test_email(email)` - Send test email

## Contributing

This module is part of the ROKCT Holdings platform. For issues or enhancements, please contact the development team.

## License

Copyright (c) 2025 ROKCT Holdings. All rights reserved.
