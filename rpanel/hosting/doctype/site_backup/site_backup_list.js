frappe.listview_settings['Site Backup'] = {
    onload: function (listview) {
        // Add bulk delete button
        listview.page.add_inner_button(__('Delete Selected'), function () {
            let selected = listview.get_checked_items();
            if (selected.length === 0) {
                frappe.msgprint(__('Please select backups to delete'));
                return;
            }

            frappe.confirm(
                `Delete ${selected.length} backup(s)?`,
                function () {
                    selected.forEach(item => {
                        frappe.call({
                            method: 'rpanel.hosting.doctype.site_backup.site_backup.delete_backup',
                            args: {
                                backup_name: item.name
                            }
                        });
                    });

                    frappe.show_alert({
                        message: __('Deleting selected backups'),
                        indicator: 'orange'
                    });

                    setTimeout(() => listview.refresh(), 2000);
                }
            );
        });
    },

    get_indicator: function (doc) {
        if (doc.status === 'Completed') {
            return [__('Completed'), 'green', 'status,=,Completed'];
        } else if (doc.status === 'Failed') {
            return [__('Failed'), 'red', 'status,=,Failed'];
        } else if (doc.status === 'In Progress') {
            return [__('In Progress'), 'blue', 'status,=,In Progress'];
        } else {
            return [__('Pending'), 'orange', 'status,=,Pending'];
        }
    },

    formatters: {
        website: function (value) {
            return `<a href="/app/hosted-website/${value}">${value}</a>`;
        },
        file_size: function (value) {
            if (!value) return '';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(value) / Math.log(k));
            return Math.round(value / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }
    }
};
