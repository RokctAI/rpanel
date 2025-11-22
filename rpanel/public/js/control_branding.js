// Control Site Branding - Replace all Frappe/ERPNext logos with ROKCT logos
frappe.ready(function () {
    applyControlBranding();
});

function applyControlBranding() {
    const logoUrl = '/assets/rokct/images/logo.svg';
    const logoDark = '/assets/rokct/images/logo_dark.svg';
    const appName = 'ROKCT Control';

    setTimeout(function () {
        // Navbar logo
        $('.navbar-brand img, .app-logo img, .navbar-home img').attr('src', logoUrl);

        // Login page logo
        $('.login-content img, .for-login img').attr('src', logoUrl);

        // Sidebar logo
        $('.sidebar-logo img').attr('src', logoUrl);

        // Splash screen logo (loading screen)
        $('.splash-logo, .app-splash img, [class*="splash"] img, .loading-logo').attr('src', logoUrl);

        // All Frappe/ERPNext logos
        $('img').each(function () {
            const src = $(this).attr('src');
            if (src && (src.includes('frappe') || src.includes('erpnext') || src.includes('logo'))) {
                // Use dark logo for dark mode if available
                const isDarkMode = $('html').attr('data-theme-mode') === 'dark';
                $(this).attr('src', isDarkMode && logoDark ? logoDark : logoUrl);
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

    // Re-apply on theme change (dark/light mode)
    $(document).on('theme-change', function () {
        const isDarkMode = $('html').attr('data-theme-mode') === 'dark';
        const currentLogo = isDarkMode && logoDark ? logoDark : logoUrl;
        $('.navbar-brand img, .app-logo img').attr('src', currentLogo);
    });

    // Update page title
    document.title = appName;

    // Hide Frappe/ERPNext branding
    const style = document.createElement('style');
    style.innerHTML = `
        .powered-by-frappe,
        .footer-powered,
        [class*="powered-by"] {
            display: none !important;
        }
    `;
    document.head.appendChild(style);
}
