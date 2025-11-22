import frappe

def get_brand_html():
    """
    Returns the brand HTML for the navbar.
    If ROKCT is installed, returns None (lets ROKCT handle it).
    Otherwise, returns RPanel branding.
    """
    # 1. Check if ROKCT is installed
    if "rokct" in frappe.get_installed_apps():
        return None
        
    # 2. Return RPanel Branding
    return "<img src='/assets/rpanel/images/rpanel_logo.svg' style='height: 24px; vertical-align: middle;'>"

def boot_session(bootinfo):
    """
    Injects RPanel branding into bootinfo.
    """
    if "rokct" in frappe.get_installed_apps():
        return

    bootinfo.sysdefaults.app_title = "RPanel"
    bootinfo.sysdefaults.app_logo_url = "/assets/rpanel/images/rpanel_logo.svg"
