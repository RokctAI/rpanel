frappe.ui.form.on('DNS Zone', {
    refresh: function (frm) {
        if (!frm.is_new()) {
            // Sync with Cloudflare button
            if (frm.doc.cloudflare_enabled) {
                frm.add_custom_button(__('Sync with Cloudflare'), function () {
                    frappe.call({
                        method: 'rpanel.hosting.doctype.dns_zone.dns_zone.sync_with_cloudflare',
                        args: {
                            zone_name: frm.doc.name
                        },
                        callback: function (r) {
                            if (r.message && r.message.success) {
                                frappe.show_alert({
                                    message: __('Synced with Cloudflare'),
                                    indicator: 'green'
                                });
                                frm.reload_doc();
                            }
                        }
                    });
                }, __('Cloudflare')).addClass('btn-primary');
            }

            // Add common records button
            frm.add_custom_button(__('Add Common Record'), function () {
                show_common_records_dialog(frm);
            }, __('DNS'));

            // Check DNS propagation
            frm.add_custom_button(__('Check Propagation'), function () {
                check_propagation_dialog(frm);
            }, __('DNS'));
        }

        // Set Cloudflare indicator
        if (frm.doc.cloudflare_enabled) {
            frm.set_df_property('cloudflare_enabled', 'description',
                '<span class="indicator-pill orange">Cloudflare Active</span>');
        }
    }
});

function show_common_records_dialog(frm) {
    frappe.call({
        method: 'rpanel.hosting.doctype.dns_zone.dns_zone.get_common_records',
        callback: function (r) {
            if (r.message) {
                let templates_html = '<div class="dns-templates">';

                r.message.forEach(template => {
                    templates_html += `
                        <div class="template-item" style="padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;"
                             onclick="add_dns_record('${template.record_type}', '${template.name_field}', '${template.value}', ${template.ttl}, ${template.priority || 0})">
                            <h4 style="margin: 0 0 5px 0;">${template.name}</h4>
                            <p style="margin: 0; color: #666; font-size: 12px;">${template.description}</p>
                            <code style="display: block; margin-top: 5px; padding: 5px; background: #f5f5f5; border-radius: 3px;">
                                ${template.record_type} ${template.name_field} → ${template.value}
                            </code>
                        </div>
                    `;
                });

                templates_html += '</div>';

                let d = new frappe.ui.Dialog({
                    title: __('Common DNS Records'),
                    fields: [
                        {
                            fieldtype: 'HTML',
                            fieldname: 'templates_html'
                        }
                    ]
                });

                d.fields_dict.templates_html.$wrapper.html(templates_html);

                // Attach global function
                window.add_dns_record = function (type, name, value, ttl, priority) {
                    let child = frm.add_child('dns_records');
                    child.record_type = type;
                    child.name_field = name;
                    child.value = value;
                    child.ttl = ttl;
                    if (priority) child.priority = priority;
                    frm.refresh_field('dns_records');
                    d.hide();
                    frappe.show_alert({
                        message: __('Record added'),
                        indicator: 'green'
                    });
                };

                d.show();
            }
        }
    });
}

function check_propagation_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Check DNS Propagation'),
        fields: [
            {
                fieldtype: 'Data',
                fieldname: 'domain',
                label: __('Domain'),
                default: frm.doc.zone_name,
                reqd: 1
            },
            {
                fieldtype: 'Select',
                fieldname: 'record_type',
                label: __('Record Type'),
                options: 'A\nAAAA\nCNAME\nMX\nTXT\nNS',
                default: 'A',
                reqd: 1
            },
            {
                fieldtype: 'HTML',
                fieldname: 'result_html'
            }
        ],
        primary_action_label: __('Check'),
        primary_action: function (values) {
            frappe.call({
                method: 'rpanel.hosting.doctype.dns_zone.dns_zone.check_dns_propagation',
                args: {
                    domain: values.domain,
                    record_type: values.record_type
                },
                callback: function (r) {
                    if (r.message) {
                        let html = '';
                        if (r.message.propagated) {
                            html = `
                                <div style="padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; margin-top: 10px;">
                                    <h4 style="color: #155724; margin: 0 0 10px 0;">✓ DNS Propagated</h4>
                                    <p style="margin: 0;"><strong>Records found:</strong></p>
                                    <ul style="margin: 5px 0;">
                                        ${r.message.records.map(rec => `<li><code>${rec}</code></li>`).join('')}
                                    </ul>
                                </div>
                            `;
                        } else {
                            html = `
                                <div style="padding: 10px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; margin-top: 10px;">
                                    <h4 style="color: #721c24; margin: 0 0 10px 0;">✗ Not Propagated</h4>
                                    <p style="margin: 0;">${r.message.error}</p>
                                </div>
                            `;
                        }
                        d.fields_dict.result_html.$wrapper.html(html);
                    }
                }
            });
        }
    });
    d.show();
}
