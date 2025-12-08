frappe.ui.form.on('Site Backup', {
    refresh: function (frm) {
        if (!frm.is_new() && frm.doc.status === 'Completed') {
            // Restore button
            frm.add_custom_button(__('Restore Backup'), function () {
                frappe.confirm(
                    `<strong>Warning:</strong> This will overwrite the current website data. Continue?`,
                    function () {
                        frappe.call({
                            method: 'rpanel.hosting.doctype.site_backup.site_backup.restore_backup',
                            args: {
                                backup_id: frm.doc.name
                            },
                            callback: function (r) {
                                if (r.message && r.message.success) {
                                    frappe.show_alert({
                                        message: __('Backup restored successfully'),
                                        indicator: 'green'
                                    });
                                } else {
                                    frappe.msgprint({
                                        title: __('Restore Failed'),
                                        message: r.message.error || 'Unknown error',
                                        indicator: 'red'
                                    });
                                }
                            }
                        });
                    }
                );
            }, __('Actions')).addClass('btn-primary');

            // Download button
            if (frm.doc.file_path) {
                frm.add_custom_button(__('Download Backup'), function () {
                    window.open(`/api/method/frappe.utils.file_manager.download_file?file_path=${encodeURIComponent(frm.doc.file_path)}`);
                }, __('Actions'));
            }

            // Delete backup button
            frm.add_custom_button(__('Delete Backup'), function () {
                frappe.confirm(
                    'Delete this backup file and record?',
                    function () {
                        frappe.call({
                            method: 'rpanel.hosting.doctype.site_backup.site_backup.delete_backup',
                            args: {
                                backup_id: frm.doc.name
                            },
                            callback: function (r) {
                                if (r.message && r.message.success) {
                                    frappe.show_alert({
                                        message: __('Backup deleted'),
                                        indicator: 'orange'
                                    });
                                    frappe.set_route('List', 'Site Backup');
                                }
                            }
                        });
                    }
                );
            }, __('Danger Zone')).addClass('btn-danger');
        }

        // Create backup button for pending backups
        if (frm.doc.status === 'Pending') {
            frm.add_custom_button(__('Create Backup Now'), function () {
                frappe.call({
                    method: 'create_backup',
                    doc: frm.doc,
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: __('Backup created successfully'),
                                indicator: 'green'
                            });
                            frm.reload_doc();
                        } else {
                            frappe.msgprint({
                                title: __('Backup Failed'),
                                message: r.message.error || 'Unknown error',
                                indicator: 'red'
                            });
                        }
                    }
                });
            }).addClass('btn-primary');
        }

        // Set status indicator
        set_backup_status_indicator(frm);

        // Format file size
        if (frm.doc.file_size) {
            frm.set_df_property('file_size', 'description',
                `<span class="text-muted">${format_bytes(frm.doc.file_size)}</span>`);
        }
    }
});

function set_backup_status_indicator(frm) {
    if (frm.doc.status === 'Completed') {
        frm.set_df_property('status', 'description',
            '<span class="indicator-pill green">Backup completed successfully</span>');
    } else if (frm.doc.status === 'Failed') {
        frm.set_df_property('status', 'description',
            '<span class="indicator-pill red">Backup failed</span>');
    } else if (frm.doc.status === 'In Progress') {
        frm.set_df_property('status', 'description',
            '<span class="indicator-pill blue">Backup in progress</span>');
    } else if (frm.doc.status === 'Pending') {
        frm.set_df_property('status', 'description',
            '<span class="indicator-pill orange">Waiting to create backup</span>');
    }
}

function format_bytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
