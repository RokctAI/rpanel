frappe.listview_settings['Cron Job'] = {
    onload: function (listview) {
        // Add bulk execute button
        listview.page.add_inner_button(__('Execute Selected'), function () {
            let selected = listview.get_checked_items();
            if (selected.length === 0) {
                frappe.msgprint(__('Please select cron jobs to execute'));
                return;
            }

            frappe.confirm(
                `Execute ${selected.length} cron job(s)?`,
                function () {
                    selected.forEach(item => {
                        frappe.call({
                            method: 'rpanel.hosting.doctype.cron_job.cron_job.execute_cron_job',
                            args: {
                                job_name: item.name
                            }
                        });
                    });

                    frappe.show_alert({
                        message: __('Executing selected cron jobs'),
                        indicator: 'blue'
                    });

                    setTimeout(() => listview.refresh(), 2000);
                }
            );
        });
    },

    get_indicator: function (doc) {
        if (!doc.enabled) {
            return [__('Disabled'), 'gray', 'enabled,=,0'];
        } else if (doc.last_status === 'Success') {
            return [__('Success'), 'green', 'last_status,=,Success'];
        } else if (doc.last_status === 'Failed') {
            return [__('Failed'), 'red', 'last_status,=,Failed'];
        } else if (doc.last_status === 'Running') {
            return [__('Running'), 'blue', 'last_status,=,Running'];
        } else {
            return [__('Pending'), 'orange', 'last_status,=,Pending'];
        }
    },

    formatters: {
        website: function (value) {
            return `<a href="/app/hosted-website/${value}">${value}</a>`;
        },
        next_run: function (value) {
            if (!value) return '';
            let date = new Date(value);
            let now = new Date();
            let diff = date - now;

            if (diff < 0) {
                return `<span style="color: red;">Overdue</span>`;
            } else if (diff < 3600000) { // Less than 1 hour
                return `<span style="color: orange;">Soon</span>`;
            } else {
                return frappe.datetime.prettyDate(value);
            }
        }
    }
};
