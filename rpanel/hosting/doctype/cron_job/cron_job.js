frappe.ui.form.on('Cron Job', {
    refresh: function (frm) {
        if (!frm.is_new()) {
            // Execute Now button
            frm.add_custom_button(__('Execute Now'), function () {
                frappe.confirm(
                    `Execute cron job "${frm.doc.job_name}" now?`,
                    function () {
                        frappe.call({
                            method: 'rpanel.hosting.doctype.cron_job.cron_job.execute_cron_job',
                            args: {
                                job_name: frm.doc.name
                            },
                            callback: function (r) {
                                if (r.message && r.message.success) {
                                    frappe.show_alert({
                                        message: __('Cron job executed successfully'),
                                        indicator: 'green'
                                    });
                                } else {
                                    frappe.show_alert({
                                        message: __('Cron job execution failed'),
                                        indicator: 'red'
                                    });
                                }
                                frm.reload_doc();
                            }
                        });
                    }
                );
            }).addClass('btn-primary');

            // Load Template button
            frm.add_custom_button(__('Load Template'), function () {
                show_template_dialog(frm);
            });

            // Validate Schedule button
            frm.add_custom_button(__('Validate Schedule'), function () {
                validate_schedule(frm);
            });
        }

        // Set status indicator
        set_status_indicator(frm);
    },

    schedule: function (frm) {
        // Auto-validate when schedule changes
        if (frm.doc.schedule) {
            validate_schedule(frm);
        }
    }
});

function set_status_indicator(frm) {
    if (frm.doc.last_status === 'Success') {
        frm.set_df_property('last_status', 'description',
            '<span class="indicator-pill green">Last execution successful</span>');
    } else if (frm.doc.last_status === 'Failed') {
        frm.set_df_property('last_status', 'description',
            '<span class="indicator-pill red">Last execution failed</span>');
    } else if (frm.doc.last_status === 'Running') {
        frm.set_df_property('last_status', 'description',
            '<span class="indicator-pill blue">Currently running</span>');
    }
}

function validate_schedule(frm) {
    if (!frm.doc.schedule) {
        frappe.msgprint(__('Please enter a cron schedule'));
        return;
    }

    frappe.call({
        method: 'rpanel.hosting.doctype.cron_job.cron_job.validate_cron_expression',
        args: {
            expression: frm.doc.schedule
        },
        callback: function (r) {
            if (r.message && r.message.valid) {
                let next_runs_html = '<ul>';
                r.message.next_runs.forEach(run => {
                    next_runs_html += `<li>${run}</li>`;
                });
                next_runs_html += '</ul>';

                frappe.msgprint({
                    title: __('Valid Cron Expression'),
                    message: `<p><strong>Next 5 executions:</strong></p>${next_runs_html}`,
                    indicator: 'green'
                });
            } else {
                frappe.msgprint({
                    title: __('Invalid Cron Expression'),
                    message: `<p>${r.message.error}</p>`,
                    indicator: 'red'
                });
            }
        }
    });
}

function show_template_dialog(frm) {
    frappe.call({
        method: 'rpanel.hosting.doctype.cron_job.cron_job.get_cron_templates',
        callback: function (r) {
            if (r.message) {
                let templates_html = '<div class="cron-templates">';

                r.message.forEach(template => {
                    templates_html += `
                        <div class="template-item" style="padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;"
                             onclick="load_template('${template.name}', '${template.command}', '${template.schedule}')">
                            <h4 style="margin: 0 0 5px 0;">${template.name}</h4>
                            <p style="margin: 0; color: #666; font-size: 12px;">${template.description}</p>
                            <code style="display: block; margin-top: 5px; padding: 5px; background: #f5f5f5; border-radius: 3px;">
                                ${template.command}
                            </code>
                            <small style="color: #999;">Schedule: ${template.schedule}</small>
                        </div>
                    `;
                });

                templates_html += '</div>';

                let d = new frappe.ui.Dialog({
                    title: __('Cron Job Templates'),
                    fields: [
                        {
                            fieldtype: 'HTML',
                            fieldname: 'templates_html'
                        }
                    ]
                });

                d.fields_dict.templates_html.$wrapper.html(templates_html);

                // Attach global function for template loading
                window.load_template = function (name, command, schedule) {
                    frm.set_value('command', command);
                    frm.set_value('schedule', schedule);
                    d.hide();
                    frappe.show_alert({
                        message: __('Template loaded: ') + name,
                        indicator: 'green'
                    });
                };

                d.show();
            }
        }
    });
}
