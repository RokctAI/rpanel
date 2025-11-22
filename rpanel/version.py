# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
import json
import os

@frappe.whitelist(allow_guest=True)
def get_version():
    # Path to the directory of this file (rpanel/rpanel/)
    module_path = os.path.abspath(os.path.dirname(__file__))
    # Path to versions.json in the same directory
    versions_file_path = os.path.join(module_path, 'versions.json')

    try:
        with open(versions_file_path, 'r') as f:
            versions = json.load(f)
        return versions.get('rpanel', '1.0.0')  # Default fallback
    except Exception:
        return '1.0.0'  # Default fallback in case of any error

__version__ = get_version()
