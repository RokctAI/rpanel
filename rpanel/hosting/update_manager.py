# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

import frappe
import subprocess
import os


@frappe.whitelist()
def update_ecosystem(immediate=False):
    """
    Triggers a pull and restart of the Docker ecosystem.
    If immediate=True, it runs now (used by CI).
    If False, it marks an update as 'Authorized' for the next maintenance window.
    """
    if not immediate:
        # Production Logic: Schedule for later
        authorize_system_update()
        return {
            "status": "success",
            "message": "Update scheduled for the next maintenance window.",
        }

    # CI / Instant Update Logic
    return perform_docker_upgrade()


def perform_docker_upgrade():
    """
    Control Hub Specific: pulls images and restarts the entire ecosystem.
    """
    print("🚀 RPanel: Starting FULL Ecosystem Upgrade...")

    try:
        compose_file = "docker-compose.yml"

        if os.path.exists(compose_file):
            print(f"--- Pulling latest images for {compose_file} ---")
            subprocess.run(
                ["docker", "compose", "-f", compose_file, "pull"], check=True
            )

            print(f"--- Performing Zero-Downtime Handover ---")
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    compose_file,
                    "up",
                    "-d",
                    "--remove-orphans",
                ],
                check=True,
            )

            return {
                "status": "success",
                "message": "Ecosystem upgrade initiated successfully.",
            }
        else:
            return {
                "status": "error",
                "message": f"Compose file {compose_file} not found.",
            }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Ecosystem Upgrade Failed")
        return {"status": "error", "message": str(e)}


def authorize_system_update():
    """
    Creates an 'Update Authorization' record to be picked up by the Sunday job.
    """
    app_name = "rpanel"
    # Detect target version from GHCR or just use 'latest'
    target_version = "latest"

    if not frappe.db.exists(
        "Update Authorization", {"app_name": app_name, "status": "Authorized"}
    ):
        doc = frappe.get_doc(
            {
                "doctype": "Update Authorization",
                "app_name": app_name,
                "target_version": target_version,
                "status": "Authorized",
                "changelog": "Automated ecosystem update",
                "authorized_by": "System",
            }
        )
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
