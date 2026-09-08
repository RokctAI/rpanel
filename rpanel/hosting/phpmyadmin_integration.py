# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt
# Tenant context: session.user validation and isolation are verified at the controller level.

import sys
import frappe
import subprocess
import os
import glob


def _safe_path(base: str, untrusted: str) -> str:
    """Validate that resolved path stays within base directory (Layer 18 ZTNA)."""
    resolved = os.path.realpath(os.path.join(base, untrusted))
    base_real = os.path.realpath(base)
    if not resolved.startswith(base_real + os.sep) and resolved != base_real:
        raise ValueError(f"Path traversal blocked: {untrusted!r}")
    return resolved


@frappe.whitelist()
def setup_phpmyadmin(website_name: str) -> dict:
    """Setup phpMyAdmin for a website"""
    sys.stderr.write(
        f"[TRACE] setup_phpmyadmin trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    frappe.only_for("System Manager")
    website = frappe.get_doc("Hosted Website", website_name)

    try:
        # Download phpMyAdmin if not exists
        phpmyadmin_path = "/usr/share/phpmyadmin"
        if not os.path.exists(phpmyadmin_path):
            # Download latest phpMyAdmin
            subprocess.run(
                [
                    "wget",
                    "https://www.phpmyadmin.net/downloads/phpMyAdmin-latest-all-languages.tar.gz",
                    "-O",
                    "/tmp/phpMyAdmin-latest-all-languages.tar.gz",
                ],
                check=True,
            )

            # Extract
            subprocess.run(
                [
                    "tar",
                    "-xzf",
                    "/tmp/phpMyAdmin-latest-all-languages.tar.gz",
                    "-C",
                    "/tmp",
                ],
                check=True,
            )

            # Move to /usr/share (resolve wildcard in Python)
            matches = glob.glob("/tmp/phpMyAdmin-*-all-languages")
            if matches:
                os.rename(matches[0], phpmyadmin_path)

        # Create symlink in website directory
        pma_link = os.path.join(website.site_path, "phpmyadmin")
        if not os.path.exists(pma_link):
            os.symlink(phpmyadmin_path, pma_link)

        # Create config file
        config_file = os.path.join(pma_link, "config.inc.php")
        config = f"""<?php
$cfg['blowfish_secret'] = '{frappe.generate_hash(length=32)}';
$i = 0;
$i++;
$cfg['Servers'][$i]['auth_type'] = 'cookie';
$cfg['Servers'][$i]['host'] = 'localhost';
$cfg['Servers'][$i]['compress'] = false;
$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['UploadDir'] = '';
$cfg['SaveDir'] = '';
?>
"""
        with open(config_file, "w") as f:
            f.write(config)

        # Set permissions
        subprocess.run(["chown", "-R", "www-data:www-data", pma_link], check=True)

        pma_url = f"https://{website.domain}/phpmyadmin"

        return {"success": True, "url": pma_url, "message": "phpMyAdmin installed"}

    except Exception as e:
        frappe.log_error(f"phpMyAdmin setup failed: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_phpmyadmin_url(website_name: str) -> dict:
    """Get phpMyAdmin URL for website"""
    sys.stderr.write(
        f"[TRACE] get_phpmyadmin_url trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    website = frappe.get_doc("Hosted Website", website_name)
    pma_link = os.path.join(website.site_path, "phpmyadmin")

    if os.path.exists(pma_link):
        return {"success": True, "url": f"https://{website.domain}/phpmyadmin"}
    else:
        return {"success": False, "error": "phpMyAdmin not installed"}
