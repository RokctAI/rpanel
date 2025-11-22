// White-label branding injection for Hosting Clients
frappe.ready(function () {
    // Get client branding
    frappe.call({
        method: 'rpanel.hosting.branding.get_client_branding_for_portal',
        callback: function (r) {
            if (r.message && r.message.enabled) {
                applyClientBranding(r.message);
            }
        }
    });
});

function applyClientBranding(branding) {
    const brandColor = branding.brand_color || '#3498db';
    const logoUrl = branding.logo;

    // Inject custom CSS
    const style = document.createElement('style');
    style.innerHTML = `
        /* Primary brand color */
        :root {
            --primary-color: ${brandColor} !important;
            --btn-primary-bg: ${brandColor} !important;
        }
        
        /* Navbar */
        .navbar {
            background-color: ${brandColor} !important;
        }
        
        /* Sidebar */
        .desk-sidebar .sidebar-item.selected,
        .desk-sidebar .sidebar-item:hover {
            background-color: ${brandColor} !important;
        }
        
        /* Buttons */
        .btn-primary,
        .btn-primary:hover,
        .btn-primary:focus,
        .btn-primary:active {
            background-color: ${brandColor} !important;
            border-color: ${brandColor} !important;
        }
        
        /* Links */
        a {
            color: ${brandColor} !important;
        }
        
        /* Indicators */
        .indicator.blue,
        .indicator-pill.blue {
            background-color: ${brandColor} !important;
        }
        
        /* Form controls */
        .form-control:focus {
            border-color: ${brandColor} !important;
            box-shadow: 0 0 0 0.2rem ${brandColor}33 !important;
        }
        
        /* Checkboxes and radios */
        .checkbox input:checked + .label-area::before,
        .radio input:checked + .label-area::before {
            background-color: ${brandColor} !important;
            border-color: ${brandColor} !important;
        }
        
        /* Progress bars */
        .progress-bar {
            background-color: ${brandColor} !important;
        }
        
        /* Tabs */
        .nav-tabs .nav-link.active {
            border-bottom-color: ${brandColor} !important;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar-thumb {
            background-color: ${brandColor} !important;
        }
        
        /* Hide Frappe branding */
        .powered-by-frappe,
        .footer-powered {
            display: none !important;
        }
    `;
    document.head.appendChild(style);

    // Replace logos
    if (logoUrl) {
        setTimeout(function () {
            // Navbar logo
            $('.navbar-brand img, .app-logo img, .navbar-home img').attr('src', logoUrl);

            // Login page logo
            $('.login-content img, .for-login img').attr('src', logoUrl);

            // Sidebar logo
            $('.sidebar-logo img').attr('src', logoUrl);

            // Splash screen logo (loading screen)
            $('.splash-logo, .app-splash img, [class*="splash"] img, .loading-logo').attr('src', logoUrl);

            // All Frappe logos
            $('img[src*="frappe"], img[src*="logo"]').each(function () {
                const src = $(this).attr('src');
                if (src && (src.includes('frappe') || src.includes('logo'))) {
                    $(this).attr('src', logoUrl);
                }
            });

            // Set favicon
            $('link[rel="icon"]').attr('href', logoUrl);
            $('link[rel="shortcut icon"]').attr('href', logoUrl);
        }, 300);

        // Re-apply on page navigation
        frappe.router.on('change', function () {
            setTimeout(function () {
                $('.navbar-brand img, .app-logo img').attr('src', logoUrl);
            }, 300);
        });
    }

    // Update page title
    if (branding.client_name) {
        document.title = branding.client_name + ' - Hosting Portal';
    }
}
