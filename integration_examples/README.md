# RPanel Integration Examples

This directory contains code snippets and examples for integrating RPanel into your own Frappe applications or Billing Systems.

## Contents

### 1. [setup.py](setup.py)
**Use Case:** You are building a "Control Plane" or "Billing App" and want to automatically install RPanel on the server when your app is installed.
**How it works:**
- It defines a `check_and_install_rpanel` function.
- Uses `bench get-app` to fetch the latest stable release from GitHub.
- Is triggered via `after_install` in your `hooks.py`.

### 2. [client_sync.py](client_sync.py)
**Use Case:** You have a subscription system and want to automatically update RPanel quotas (Storage, Max Sites) when a customer changes their plan.
**How it works:**
- Shows how to access the `Hosting Client` DocType.
- Syncs fields like `max_websites`, `max_storage_gb`, etc.

## Best Practices

- **Always use `rpanel.hosting.utils`**: Instead of writing raw SQL, import utilities from RPanel to ensure data integrity.
- **Check for Installation**: Always wrap your imports in a `try/except` block or check `frappe.get_installed_apps()` if your app can run without RPanel.
