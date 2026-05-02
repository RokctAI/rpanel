# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

import click
import frappe

@click.command("update-ecosystem")
@click.option("--immediate", is_flag=True, help="Run the update immediately (CI/Manual)")
def update_ecosystem_command(immediate=False):
    """
    Pulls latest Docker images and restarts the RPanel ecosystem.
    """
    from rpanel.hosting.update_manager import update_ecosystem
    
    # We need to initialize frappe if not already initialized
    # (Though bench execute usually handles this, direct commands might need it)
    if not frappe.local.site:
        print("Please provide a site using --site [site]")
        return

    result = update_ecosystem(immediate=immediate)
    if result.get("status") == "success":
        print(f"✅ {result.get('message')}")
    else:
        print(f"❌ {result.get('message')}")

commands = [
    update_ecosystem_command
]
