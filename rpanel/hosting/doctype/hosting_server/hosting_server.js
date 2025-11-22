// Copyright (c) 2025, Rendani Sinyage and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hosting Server', {
    refresh: function (frm) {
        // Add custom buttons
        if (!frm.is_new()) {
            // Provision Server button
            frm.add_custom_button(__('Provision Server'), function () {
                frappe.confirm(
                    'This will automatically install Nginx, MariaDB, PHP, Certbot, Email services, and other required software on this server. Continue?',
                    function () {
                        frappe.call({
                            method: 'rpanel.hosting.server_provisioner.provision_server',
                            args: {
                                server_name: frm.doc.name
                            },
                            freeze: true,
                            freeze_message: __('Provisioning server... This may take 10-15 minutes'),
                            callback: function (r) {
                                if (r.message && r.message.success) {
                                    frappe.show_alert({
                                        message: __('Server provisioned successfully!'),
                                        indicator: 'green'
                                    });
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Actions'));

            // Check Services button
            frm.add_custom_button(__('Check Services'), function () {
                frappe.call({
                    method: 'rpanel.hosting.server_provisioner.check_server_services',
                    args: {
                        server_name: frm.doc.name
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.msgprint({
                                title: __('Installed Services'),
                                message: '<pre>' + r.message.services + '</pre>',
                                indicator: 'blue'
                            });
                        }
                    }
                });
            }, __('Actions'));

            // Test Connection button
            frm.add_custom_button(__('Test Connection'), function () {
                frappe.call({
                    method: 'rpanel.hosting.doctype.hosting_server.hosting_server.test_connection',
                    args: {
                        server_name: frm.doc.name
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({
                                message: __('Connection successful!'),
                                indicator: 'green'
                            });
                        } else {
                            frappe.msgprint({
                                title: __('Connection Failed'),
                                message: r.message.error || 'Unknown error',
                                indicator: 'red'
                            });
                        }
                    }
                });
            }, __('Actions'));

            // Get Server Resources button
            frm.add_custom_button(__('View Resources'), function () {
                frappe.call({
                    method: 'rpanel.hosting.doctype.hosting_server.hosting_server.get_server_resources',
                    args: {
                        server_name: frm.doc.name
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            let msg = `
                                <h4>Server Resources</h4>
                                <table class="table table-bordered">
                                    <tr><td><b>CPU Usage:</b></td><td>${r.message.cpu_usage}%</td></tr>
                                    <tr><td><b>Memory Usage:</b></td><td>${r.message.memory_usage}%</td></tr>
                                    <tr><td><b>Disk Usage:</b></td><td>${r.message.disk_usage}%</td></tr>
                                    <tr><td><b>Load Average:</b></td><td>${r.message.load_average}</td></tr>
                                </table>
                            `;
                            frappe.msgprint({
                                title: __('Server Resources'),
                                message: msg,
                                indicator: 'blue'
                            });
                        }
                    }
                });
            }, __('Actions'));
        }
    }
});
