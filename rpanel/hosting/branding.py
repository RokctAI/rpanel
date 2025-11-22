# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def get_client_branding(user=None):
    """Get branding settings for the current user's client"""
    if not user:
        user = frappe.session.user
    
    # Check if user is linked to a hosting client
    client = frappe.db.get_value('Hosting Client', {'email': user}, 
                                  ['name', 'custom_logo', 'brand_color', 'portal_enabled'], 
                                  as_dict=True)
    
    if client and client.portal_enabled:
        return {
            'enabled': True,
            'logo': client.custom_logo,
            'brand_color': client.brand_color or '#3498db',
            'client_name': client.name
        }
    
    return {'enabled': False}


def get_brand_html():
    """Generate custom branding HTML/CSS"""
    branding = get_client_branding()
    
    if not branding.get('enabled'):
        return ""
    
    brand_color = branding.get('brand_color', '#3498db')
    logo_url = branding.get('logo', '')
    
    # Generate custom CSS
    custom_css = f"""
    <style>
        /* Replace Frappe branding colors */
        :root {{
            --primary-color: {brand_color} !important;
            --btn-primary-bg: {brand_color} !important;
        }}
        
        /* Navbar branding */
        .navbar {{
            background-color: {brand_color} !important;
        }}
        
        /* Sidebar active items */
        .desk-sidebar .sidebar-item.selected {{
            background-color: {brand_color} !important;
        }}
        
        /* Primary buttons */
        .btn-primary {{
            background-color: {brand_color} !important;
            border-color: {brand_color} !important;
        }}
        
        .btn-primary:hover {{
            background-color: {brand_color} !important;
            opacity: 0.9;
        }}
        
        /* Links */
        a {{
            color: {brand_color} !important;
        }}
        
        /* Indicators */
        .indicator.blue {{
            background-color: {brand_color} !important;
        }}
        
        /* Form focus */
        .form-control:focus {{
            border-color: {brand_color} !important;
        }}
        
        /* Custom scrollbar */
        ::-webkit-scrollbar-thumb {{
            background-color: {brand_color} !important;
        }}
    </style>
    """
    
    # Logo replacement script
    logo_script = ""
    if logo_url:
        logo_script = f"""
        <script>
            frappe.ready(function() {{
                // Replace navbar logo
                setTimeout(function() {{
                    $('.navbar-brand img, .app-logo img').attr('src', '{logo_url}');
                    $('.navbar-home img').attr('src', '{logo_url}');
                    
                    // Replace login page logo
                    $('.login-content img').attr('src', '{logo_url}');
                    
                    // Replace all Frappe logos
                    $('img[src*="frappe"]').each(function() {{
                        if ($(this).attr('src').includes('logo')) {{
                            $(this).attr('src', '{logo_url}');
                        }}
                    }});
                }}, 500);
            }});
        </script>
        """
    
    return custom_css + logo_script


@frappe.whitelist(allow_guest=True)
def get_client_branding_for_portal():
    """API endpoint to get branding for current user"""
    branding = get_client_branding()
    return branding


def apply_branding_to_page(context):
    """Hook to inject branding into page context"""
    branding = get_client_branding()
    
    if branding.get('enabled'):
        context['custom_branding'] = get_brand_html()
        context['brand_logo'] = branding.get('logo')
        context['brand_color'] = branding.get('brand_color')
        context['client_name'] = branding.get('client_name')
    
    return context
