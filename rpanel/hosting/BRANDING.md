# White-Label Branding System

## Overview
Complete white-label branding system that replaces Frappe logos and applies custom CSS based on client settings.

## Features

### 1. Custom Logo Replacement
- Replaces all Frappe logos with client's custom logo
- Updates navbar, sidebar, login page, and favicon
- Persists across page navigation

### 2. Custom Brand Colors
- Applies client's brand color to:
  - Primary buttons
  - Links
  - Navbar
  - Sidebar active items
  - Form focus states
  - Progress bars
  - Indicators
  - Scrollbars

### 3. Frappe Branding Removal
- Hides "Powered by Frappe" footer
- Removes Frappe logos
- Updates page title with client name

## Setup

### 1. Configure Client Branding

Navigate to: **Hosting > Hosting Client**

Enable branding:
```
Portal Enabled: ✓ (checked)
Custom Logo: [Upload logo image]
Brand Color: #FF5733 (or any hex color)
```

### 2. Create Portal User

The client's email will be used to identify them:
```python
# Automatically done when portal is enabled
client.email = "admin@acme.com"
```

### 3. Login as Client

When the client logs in with their email, branding is automatically applied.

## How It Works

### Backend (`branding.py`)
- Detects user's client based on email
- Retrieves branding settings
- Generates custom CSS
- Provides API for frontend

### Frontend (`hosting_branding.js`)
- Loads on every page
- Fetches client branding via API
- Injects custom CSS
- Replaces logos dynamically
- Reapplies on navigation

## Customization

### Add More Branding Elements

Edit `hosting_branding.js`:
```javascript
// Add custom footer
$('.footer').html(`
    <p>© 2025 ${branding.client_name}. All rights reserved.</p>
`);
```

### Custom CSS Rules

Edit the CSS in `hosting_branding.js`:
```javascript
style.innerHTML = `
    /* Your custom CSS */
    .custom-element {
        color: ${brandColor};
    }
`;
```

## API Reference

### Get Client Branding
```python
branding = frappe.call('rpanel.hosting.branding.get_client_branding_for_portal')
```

Returns:
```json
{
    "enabled": true,
    "logo": "/files/client_logo.png",
    "brand_color": "#FF5733",
    "client_name": "Acme Corp"
}
```

## Testing

1. Create a test client
2. Enable portal and upload logo
3. Set brand color
4. Login with client email
5. Verify branding is applied

## Notes

- Branding is user-specific (based on email)
- Changes apply immediately after login
- No server restart required
- Works with all Frappe pages
