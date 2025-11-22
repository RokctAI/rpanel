import frappe

def get_brand_html():
    """
    Returns the brand HTML for the navbar.
    If ROKCT is installed, returns None (lets ROKCT handle it).
    Otherwise, returns RPanel branding.
    """
    # 1. Check if ROKCT is installed
    if "control" in frappe.get_installed_apps():
        # Use ROKCT's branding settings if available
        # This allows centralization of branding in the Control Plane
        try:
            return frappe.get_doc("Control Branding Settings")
        except Exception:
            pass

    return None

def boot_session(bootinfo):
    """
    Injects RPanel branding into bootinfo.
    """
    if "control" in frappe.get_installed_apps():
        return

    bootinfo.sysdefaults.app_title = "RPanel"
    bootinfo.sysdefaults.app_logo_url = "/assets/rpanel/images/rpanel_logo.svg"

def get_client_branding():
    """
    Get branding for client portal
    """
    if "control" in frappe.get_installed_apps():
        return

    bootinfo.sysdefaults.app_title = "RPanel"
    bootinfo.sysdefaults.app_logo_url = "/assets/rpanel/images/rpanel_logo.svg"
