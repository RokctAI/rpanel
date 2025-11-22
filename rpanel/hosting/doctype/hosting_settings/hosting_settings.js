frappe.ui.form.on('Hosting Settings', {
    refresh: function (frm) {
        // Enhance button descriptions
        frm.fields_dict['renew_platform_ssl'].$input.addClass('btn-primary');
        frm.fields_dict['renew_wildcard_ssl'].$input.addClass('btn-primary');
        frm.fields_dict['install_roundcube'].$input.addClass('btn-success');

        // Add help text
        frm.set_df_property('platform_cert_command', 'description',
            'Command to renew the platform SSL certificate. Uses sudo by default.');

        frm.set_df_property('wildcard_cert_command', 'description',
            'Command to renew wildcard SSL certificate. Typically uses bench command.');

        frm.set_df_property('nginx_config_path', 'description',
            'Path where Nginx site configurations are stored. Default: /etc/nginx/conf.d');

        frm.set_df_property('web_root_base', 'description',
            'Base directory for hosting website files. Default: /var/www');

        // Add system info section
        frm.add_custom_button(__('Check System Status'), function () {
            frappe.call({
                method: 'rpanel.hosting.doctype.hosting_settings.hosting_settings.get_system_status',
                callback: function (r) {
                    if (r.message) {
                        let status_html = '<div class="frappe-control">';
                        status_html += '<h4>System Status</h4>';
                        status_html += '<table class="table table-bordered">';

                        for (let key in r.message) {
                            let value = r.message[key];
                            let indicator = value.status === 'running' ? 'green' : 'red';
                            status_html += `<tr>
                                <td><strong>${key}</strong></td>
                                <td><span class="indicator-pill ${indicator}">${value.status}</span></td>
                            </tr>`;
                        }

                        status_html += '</table></div>';

                        frappe.msgprint({
                            title: __('System Status'),
                            message: status_html,
                            indicator: 'blue'
                        });
                    }
                }
            });
        }, __('System Tools'));

        frm.add_custom_button(__('Reload Nginx'), function () {
            frappe.confirm(
                'Reload Nginx configuration?',
                function () {
                    frappe.call({
                        method: 'rpanel.hosting.doctype.hosting_settings.hosting_settings.reload_nginx',
                        callback: function (r) {
                            frappe.show_alert({
                                message: __('Nginx reloaded successfully'),
                                indicator: 'green'
                            });
                        }
                    });
                }
            );
        }, __('System Tools'));

        frm.add_custom_button(__('Test Email Config'), function () {
            frappe.prompt({
                label: 'Test Email Address',
                fieldname: 'email',
                fieldtype: 'Data',
                reqd: 1
            }, function (values) {
                frappe.call({
                    method: 'rpanel.hosting.doctype.hosting_settings.hosting_settings.test_email',
                    args: {
                        email: values.email
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.msgprint(__('Test email sent successfully'));
                        } else {
                            frappe.msgprint(__('Email test failed. Check logs.'));
                        }
                    }
                });
            }, __('Send Test Email'));
        }, __('System Tools'));
    }
});
