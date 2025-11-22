frappe.listview_settings['Hosted Website'] = {
    add_fields: ['status', 'ssl_status', 'domain', 'site_type'],

    get_indicator: function (doc) {
        if (doc.status === 'Active') {
            if (doc.ssl_status === 'Active') {
                return [__('Active (SSL)'), 'green', 'status,=,Active'];
            }
            return [__('Active'), 'blue', 'status,=,Active'];
        } else if (doc.status === 'Pending') {
            return [__('Pending'), 'orange', 'status,=,Pending'];
        } else if (doc.status === 'Suspended') {
            return [__('Suspended'), 'red', 'status,=,Suspended'];
        } else if (doc.status === 'Error') {
            return [__('Error'), 'red', 'status,=,Error'];
        }
    },

    onload: function (listview) {
        // Add custom bulk actions
        listview.page.add_action_item(__('Provision Selected'), function () {
            let selected = listview.get_checked_items();
            if (selected.length === 0) {
                frappe.msgprint(__('Please select websites to provision'));
                return;
            }

            frappe.confirm(
                __('Provision {0} selected website(s)?', [selected.length]),
                function () {
                    selected.forEach(function (doc) {
                        frappe.call({
                            method: 'rpanel.hosting.doctype.hosted_website.hosted_website.provision_site',
                            args: {
                                name: doc.name
                            },
                            callback: function (r) {
                                frappe.show_alert({
                                    message: __('Provisioning {0}', [doc.name]),
                                    indicator: 'green'
                                });
                            }
                        });
                    });
                    setTimeout(function () {
                        listview.refresh();
                    }, 2000);
                }
            );
        });

        // Add filter shortcuts
        listview.page.add_inner_button(__('Active Sites'), function () {
            listview.filter_area.clear();
            listview.filter_area.add([[listview.doctype, 'status', '=', 'Active']]);
        }, __('Filters'));

        listview.page.add_inner_button(__('SSL Enabled'), function () {
            listview.filter_area.clear();
            listview.filter_area.add([[listview.doctype, 'ssl_status', '=', 'Active']]);
        }, __('Filters'));

        listview.page.add_inner_button(__('WordPress Sites'), function () {
            listview.filter_area.clear();
            listview.filter_area.add([
                [listview.doctype, 'site_type', '=', 'CMS'],
                [listview.doctype, 'cms_type', '=', 'WordPress']
            ]);
        }, __('Filters'));
    },

    formatters: {
        domain: function (value, df, doc) {
            if (doc.ssl_status === 'Active') {
                return `<a href="https://${value}" target="_blank">${value} <i class="fa fa-lock text-success"></i></a>`;
            } else {
                return `<a href="http://${value}" target="_blank">${value}</a>`;
            }
        }
    }
};
