"""
RPanel Integration: Client Sync Logic
=====================================

Use this code to sync your Billing/Subscription system with RPanel Hosting Clients.

How to use:
1. Import `rpanel.hosting.utils` (Available after RPanel is installed).
2. Call `sync_client_quotas` when a user upgrades their plan.

"""

import frappe

def sync_client_quotas(client_name, plan_doc):
    """
    Syncs Hosting Client quotas (Validates RPanel fields).
    
    Args:
        client_name (str): Name of the Hosting Client (usually Customer name).
        plan_doc (doc): Your Subscription Plan document.
    """
    if not frappe.db.exists('Hosting Client', client_name):
        return

    client = frappe.get_doc('Hosting Client', client_name)

    # Example: Sync fields if they exist in your plan
    if hasattr(plan_doc, 'max_websites'):
        client.max_websites = plan_doc.max_websites

    if hasattr(plan_doc, 'max_storage_gb'):
        client.max_storage_gb = plan_doc.max_storage_gb

    if hasattr(plan_doc, 'max_databases'):
        client.max_databases = plan_doc.max_databases

    client.save()
    print(f"Synced {client_name} with plan {plan_doc.name}")
