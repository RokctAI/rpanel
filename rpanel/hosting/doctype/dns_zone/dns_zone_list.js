frappe.listview_settings['DNS Zone'] = {
    onload: function (listview) {
        // Add bulk sync button
        listview.page.add_inner_button(__('Sync with Cloudflare'), function () {
            let selected = listview.get_checked_items();
            if (selected.length === 0) {
                frappe.msgprint(__('Please select DNS zones to sync'));
                return;
            }

            selected.forEach(item => {
                frappe.call({
                    method: 'rpanel.hosting.doctype.dns_zone.dns_zone.sync_with_cloudflare',
                    args: {
                        zone_name: item.name
                    }
                });
            });

            frappe.show_alert({
                message: __('Syncing selected zones'),
                indicator: 'blue'
            });

            setTimeout(() => listview.refresh(), 2000);
        });
    },

    get_indicator: function (doc) {
        if (doc.cloudflare_enabled) {
            return [__('Cloudflare'), 'orange', 'cloudflare_enabled,=,1'];
        } else {
            return [__('Local'), 'gray', 'cloudflare_enabled,=,0'];
        }
    },

    formatters: {
        website: function (value) {
            if (!value) return '';
            return `<a href="/app/hosted-website/${value}">${value}</a>`;
        }
    }
};
