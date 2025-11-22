frappe.ui.form.on('Hosted Website', {
    refresh: function (frm) {
        // Auto-set client if not set and user is not admin
        if (!frm.doc.client && !frappe.user.has_role('System Manager')) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Hosting Client',
                    filters: { 'email': frappe.session.user },
                    fieldname: 'name'
                },
                callback: function (r) {
                    if (r.message && r.message.name) {
                        frm.set_value('client', r.message.name);
                    }
                }
            });
        }

        // Add custom buttons based on status
        if (!frm.is_new()) {
            // Provision/Re-provision button
            if (frm.doc.status === 'Active') {
                frm.add_custom_button(__('Provision Site'), function () {
                    frappe.confirm(
                        'This will provision/re-provision the website. Continue?',
                        function () {
                            frappe.call({
                                method: 'provision_site',
                                doc: frm.doc,
                                callback: function (r) {
                                    frappe.show_alert({
                                        message: __('Site provisioning started'),
                                        indicator: 'green'
                                    });
                                    frm.reload_doc();
                                }
                            });
                        }
                    );
                }).addClass('btn-primary');
            }

            // SSL Management buttons
            frm.add_custom_button(__('Issue SSL Certificate'), function () {
                frappe.confirm(
                    'This will request an SSL certificate from Let\'s Encrypt. Continue?',
                    function () {
                        frappe.call({
                            method: 'issue_ssl',
                            doc: frm.doc,
                            callback: function (r) {
                                frappe.show_alert({
                                    message: __('SSL certificate request initiated'),
                                    indicator: 'blue'
                                });
                                frm.reload_doc();
                            }
                        });
                    }
                );
            }, __('SSL'));

            // Quick links section
            frm.add_custom_button(__('Open Website'), function () {
                const protocol = frm.doc.ssl_status === 'Active' ? 'https' : 'http';
                window.open(`${protocol}://${frm.doc.domain}`, '_blank');
            }, __('Quick Actions'));

            if (frm.doc.site_type === 'CMS' && frm.doc.cms_type === 'WordPress') {
                frm.add_custom_button(__('WordPress Admin'), function () {
                    const protocol = frm.doc.ssl_status === 'Active' ? 'https' : 'http';
                    window.open(`${protocol}://${frm.doc.domain}/wp-admin`, '_blank');
                }, __('Quick Actions'));
            }

            frm.add_custom_button(__('Webmail'), function () {
                const protocol = frm.doc.ssl_status === 'Active' ? 'https' : 'http';
                window.open(`${protocol}://${frm.doc.domain}/webmail`, '_blank');
            }, __('Quick Actions'));

            frm.add_custom_button(__('File Manager'), function () {
                open_file_manager(frm);
            }, __('Quick Actions'));

            // Backup & Restore section
            frm.add_custom_button(__('Create Backup'), function () {
                show_backup_dialog(frm);
            }, __('Backup'));

            frm.add_custom_button(__('View Backups'), function () {
                frappe.set_route('List', 'Site Backup', { website: frm.doc.name });
            }, __('Backup'));

            // Git Deployment section
            frm.add_custom_button(__('Clone Repository'), function () {
                show_git_clone_dialog(frm);
            }, __('Git'));

            frm.add_custom_button(__('Pull Latest'), function () {
                frappe.call({
                    method: 'rpanel.hosting.git_manager.pull_latest',
                    args: { website_name: frm.doc.name },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({ message: __('Pulled latest changes'), indicator: 'green' });
                        } else {
                            frappe.msgprint({ title: __('Pull Failed'), message: r.message.error, indicator: 'red' });
                        }
                    }
                });
            }, __('Git'));

            frm.add_custom_button(__('Deployment History'), function () {
                show_deployment_history(frm);
            }, __('Git'));

            frm.add_custom_button(__('Setup Webhook'), function () {
                show_webhook_dialog(frm);
            }, __('Git'));

            // Log Viewer
            frm.add_custom_button(__('View Logs'), function () {
                show_log_viewer(frm);
            }, __('Logs'));

            // Deprovision button (danger)
            frm.add_custom_button(__('Deprovision Site'), function () {
                frappe.confirm(
                    'This will remove the site configuration. The site directory will be archived. Continue?',
                    function () {
                        frappe.call({
                            method: 'deprovision_site',
                            doc: frm.doc,
                            callback: function (r) {
                                frappe.show_alert({
                                    message: __('Site deprovisioned'),
                                    indicator: 'orange'
                                });
                                frm.reload_doc();
                            }
                        });
                    }
                );
            }, __('Danger Zone')).addClass('btn-danger');
        }

        // Set field indicators
        frm.trigger('set_indicators');
    },

    set_indicators: function (frm) {
        // SSL Status indicator
        if (frm.doc.ssl_status === 'Active') {
            frm.set_df_property('ssl_status', 'description',
                '<span class="indicator-pill green">SSL Active</span>');
        } else if (frm.doc.ssl_status === 'Failed') {
            frm.set_df_property('ssl_status', 'description',
                '<span class="indicator-pill red">SSL Failed - Check logs</span>');
        } else {
            frm.set_df_property('ssl_status', 'description',
                '<span class="indicator-pill orange">No SSL</span>');
        }

        // Status indicator
        if (frm.doc.status === 'Active') {
            frm.set_df_property('status', 'description',
                '<span class="indicator-pill green">Site is active</span>');
        } else if (frm.doc.status === 'Pending') {
            frm.set_df_property('status', 'description',
                '<span class="indicator-pill orange">Awaiting provisioning</span>');
        } else if (frm.doc.status === 'Error') {
            frm.set_df_property('status', 'description',
                '<span class="indicator-pill red">Error - Check logs</span>');
        }
    },

    site_type: function (frm) {
        // Show/hide CMS-related fields
        if (frm.doc.site_type === 'CMS') {
            frm.set_df_property('cms_type', 'reqd', 1);
            frm.set_df_property('db_name', 'reqd', 1);
            frm.set_df_property('db_user', 'reqd', 1);
        } else {
            frm.set_df_property('cms_type', 'reqd', 0);
            frm.set_df_property('db_name', 'reqd', 0);
            frm.set_df_property('db_user', 'reqd', 0);
        }

        // Frappe Tenant Logic
        if (frm.doc.site_type == 'Frappe Tenant') {
            if (!frm.doc.client) {
                frappe.msgprint(__("Please select a Hosting Client first."));
                frm.set_value('site_type', 'HTML');
                return;
            }

            // Check Client's Plan for 'Frappe Tenancy' module
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Hosting Client',
                    name: frm.doc.client
                },
                callback: function (r) {
                    if (r.message) {
                        let client = r.message;
                        // We need to check the Subscription Plan linked to this client
                        if (client.plan_type) {
                            frappe.call({
                                method: 'frappe.client.get',
                                args: {
                                    doctype: 'Subscription Plan',
                                    name: client.plan_type
                                },
                                callback: function (plan_r) {
                                    if (plan_r.message) {
                                        let plan = plan_r.message;
                                        let has_frappe_tenancy = false;

                                        // Check modules child table
                                        if (plan.modules) {
                                            for (let m of plan.modules) {
                                                if (m.module === 'Frappe Tenancy') {
                                                    has_frappe_tenancy = true;
                                                    break;
                                                }
                                            }
                                        }

                                        if (!has_frappe_tenancy) {
                                            frappe.msgprint({
                                                title: __('Upgrade Required'),
                                                indicator: 'orange',
                                                message: __('Frappe Tenant creation is only available on Enterprise plans. Please upgrade your subscription.')
                                            });
                                            frm.set_value('site_type', 'HTML');
                                        }
                                    }
                                }
                            });
                        }
                    }
                }
            });
        }
    },

    domain: function (frm) {
        // Auto-generate safe database name from domain
        if (frm.doc.domain && !frm.doc.db_name && frm.doc.site_type === 'CMS') {
            let safe_name = frm.doc.domain.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 16);
            frm.set_value('db_name', safe_name);
            frm.set_value('db_user', safe_name);
        }
    },

    status: function (frm) {
        frm.trigger('set_indicators');
    },

    ssl_status: function (frm) {
        frm.trigger('set_indicators');
    }
});

// File Manager Dialog
function open_file_manager(frm) {
    let current_path = '';

    let d = new frappe.ui.Dialog({
        title: __('File Manager - {0}', [frm.doc.domain]),
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'file_browser'
            }
        ]
    });

    function load_files(path = '') {
        current_path = path;

        frappe.call({
            method: 'rpanel.hosting.file_manager.get_file_list',
            args: {
                website_name: frm.doc.name,
                path: path
            },
            callback: function (r) {
                if (r.message) {
                    render_file_browser(r.message, d);
                }
            }
        });
    }

    function render_file_browser(data, dialog) {
        let html = `
            <div class="file-manager-container">
                <div class="file-manager-toolbar">
                    <button class="btn btn-sm btn-default" onclick="file_manager_go_back()">
                        <i class="fa fa-arrow-left"></i> Back
                    </button>
                    <span class="file-manager-path">${data.current_path || '/'}</span>
                    <button class="btn btn-sm btn-primary" onclick="file_manager_upload()">
                        <i class="fa fa-upload"></i> Upload
                    </button>
                    <button class="btn btn-sm btn-success" onclick="file_manager_new_folder()">
                        <i class="fa fa-folder"></i> New Folder
                    </button>
                </div>
                <div class="file-manager-list">
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th width="50%">Name</th>
                                <th width="15%">Size</th>
                                <th width="20%">Modified</th>
                                <th width="15%">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        data.items.forEach(item => {
            const icon = item.is_dir ? 'fa-folder' : 'fa-file';
            const size = item.is_dir ? '-' : format_file_size(item.size);
            const date = new Date(item.modified * 1000).toLocaleString();

            html += `
                <tr>
                    <td>
                        <i class="fa ${icon}"></i>
                        ${item.is_dir ?
                    `<a href="#" onclick="file_manager_open_folder('${item.path}')">${item.name}</a>` :
                    `<span>${item.name}</span>`
                }
                    </td>
                    <td>${size}</td>
                    <td>${date}</td>
                    <td>
                        ${!item.is_dir ? `<button class="btn btn-xs btn-default" onclick="file_manager_download('${item.path}')">
                            <i class="fa fa-download"></i>
                        </button>` : ''}
                        ${!item.is_dir && is_text_file(item.name) ? `<button class="btn btn-xs btn-default" onclick="file_manager_edit('${item.path}')">
                            <i class="fa fa-edit"></i>
                        </button>` : ''}
                        <button class="btn btn-xs btn-danger" onclick="file_manager_delete('${item.path}', ${item.is_dir})">
                            <i class="fa fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        });

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
            <style>
                .file-manager-container { padding: 10px; }
                .file-manager-toolbar { margin-bottom: 15px; padding: 10px; background: #f5f5f5; border-radius: 4px; }
                .file-manager-path { margin: 0 15px; font-family: monospace; }
                .file-manager-list { max-height: 400px; overflow-y: auto; }
            </style>
        `;

        dialog.fields_dict.file_browser.$wrapper.html(html);

        // Attach global functions
        window.file_manager_open_folder = function (path) {
            load_files(path);
        };

        window.file_manager_go_back = function () {
            if (current_path) {
                const parent = current_path.split('/').slice(0, -1).join('/');
                load_files(parent);
            }
        };

        window.file_manager_download = function (path) {
            window.open(`/api/method/rpanel.hosting.file_manager.download_file?website_name=${frm.doc.name}&file_path=${encodeURIComponent(path)}`);
        };

        window.file_manager_delete = function (path, is_dir) {
            frappe.confirm(
                `Delete ${is_dir ? 'folder' : 'file'}: ${path}?`,
                function () {
                    frappe.call({
                        method: 'rpanel.hosting.file_manager.delete_file',
                        args: {
                            website_name: frm.doc.name,
                            file_path: path
                        },
                        callback: function (r) {
                            if (r.message && r.message.success) {
                                frappe.show_alert({ message: __('Deleted successfully'), indicator: 'green' });
                                load_files(current_path);
                            }
                        }
                    });
                }
            );
        };

        window.file_manager_upload = function () {
            const upload_dialog = new frappe.ui.Dialog({
                title: __('Upload File'),
                fields: [
                    {
                        fieldtype: 'Attach',
                        fieldname: 'file',
                        label: __('Select File'),
                        reqd: 1
                    }
                ],
                primary_action_label: __('Upload'),
                primary_action: function (values) {
                    if (values.file) {
                        // Get file data
                        frappe.call({
                            method: 'frappe.client.get_value',
                            args: {
                                doctype: 'File',
                                filters: { file_url: values.file },
                                fieldname: ['file_name', 'content']
                            },
                            callback: function (r) {
                                if (r.message) {
                                    frappe.call({
                                        method: 'rpanel.hosting.file_manager.upload_file',
                                        args: {
                                            website_name: frm.doc.name,
                                            path: current_path,
                                            filename: r.message.file_name,
                                            filedata: r.message.content
                                        },
                                        callback: function (r) {
                                            if (r.message && r.message.success) {
                                                frappe.show_alert({ message: __('Uploaded successfully'), indicator: 'green' });
                                                upload_dialog.hide();
                                                load_files(current_path);
                                            }
                                        }
                                    });
                                }
                            }
                        });
                    }
                }
            });
            upload_dialog.show();
        };

        window.file_manager_new_folder = function () {
            frappe.prompt({
                label: __('Folder Name'),
                fieldname: 'dirname',
                fieldtype: 'Data',
                reqd: 1
            }, function (values) {
                frappe.call({
                    method: 'rpanel.hosting.file_manager.create_directory',
                    args: {
                        website_name: frm.doc.name,
                        path: current_path,
                        dirname: values.dirname
                    },
                    callback: function (r) {
                        if (r.message && r.message.success) {
                            frappe.show_alert({ message: __('Folder created'), indicator: 'green' });
                            load_files(current_path);
                        }
                    }
                });
            }, __('Create New Folder'));
        };

        window.file_manager_edit = function (path) {
            frappe.call({
                method: 'rpanel.hosting.file_manager.read_file',
                args: {
                    website_name: frm.doc.name,
                    file_path: path
                },
                callback: function (r) {
                    if (r.message) {
                        const edit_dialog = new frappe.ui.Dialog({
                            title: __('Edit File: {0}', [path]),
                            size: 'large',
                            fields: [
                                {
                                    fieldtype: 'Code',
                                    fieldname: 'content',
                                    label: __('Content'),
                                    options: get_language_from_filename(path)
                                }
                            ],
                            primary_action_label: __('Save'),
                            primary_action: function (values) {
                                frappe.call({
                                    method: 'rpanel.hosting.file_manager.save_file',
                                    args: {
                                        website_name: frm.doc.name,
                                        file_path: path,
                                        content: values.content
                                    },
                                    callback: function (r) {
                                        if (r.message && r.message.success) {
                                            frappe.show_alert({ message: __('File saved'), indicator: 'green' });
                                            edit_dialog.hide();
                                        }
                                    }
                                });
                            }
                        });
                        edit_dialog.set_value('content', r.message.content);
                        edit_dialog.show();
                    }
                }
            });
        };
    }

    function format_file_size(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    function is_text_file(filename) {
        const text_extensions = ['.txt', '.php', '.html', '.css', '.js', '.json', '.xml', '.md', '.py', '.sh', '.conf', '.htaccess'];
        return text_extensions.some(ext => filename.toLowerCase().endsWith(ext));
    }

    function get_language_from_filename(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const lang_map = {
            'php': 'PHP',
            'html': 'HTML',
            'css': 'CSS',
            'js': 'JavaScript',
            'json': 'JSON',
            'xml': 'XML',
            'py': 'Python',
            'sh': 'Shell'
        };
        return lang_map[ext] || 'Text';
    }

    d.show();
    load_files('');
}

// Backup Dialog
function show_backup_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Create Backup'),
        fields: [
            {
                fieldtype: 'Select',
                fieldname: 'backup_type',
                label: __('Backup Type'),
                options: 'Full\nDatabase Only\nFiles Only',
                default: 'Full',
                reqd: 1
            },
            {
                fieldtype: 'Check',
                fieldname: 'upload_to_cloud',
                label: __('Upload to Cloud Storage')
            },
            {
                fieldtype: 'Select',
                fieldname: 'cloud_storage',
                label: __('Cloud Storage'),
                options: 'None\nAWS S3\nGoogle Cloud Storage\nDropbox',
                default: 'None',
                depends_on: 'upload_to_cloud'
            },
            {
                fieldtype: 'Small Text',
                fieldname: 'notes',
                label: __('Notes')
            }
        ],
        primary_action_label: __('Create Backup'),
        primary_action: function (values) {
            frappe.call({
                method: 'rpanel.hosting.doctype.site_backup.site_backup.create_backup',
                args: {
                    website_name: frm.doc.name,
                    backup_type: values.backup_type,
                    upload_to_cloud: values.upload_to_cloud,
                    cloud_storage: values.cloud_storage
                },
                callback: function (r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Backup created successfully'),
                            indicator: 'green'
                        });
                        d.hide();
                    } else {
                        frappe.msgprint({
                            title: __('Backup Failed'),
                            message: r.message.error || 'Unknown error',
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    });
    d.show();
}

// Git Clone Dialog
function show_git_clone_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Clone Git Repository'),
        fields: [
            {
                fieldtype: 'Data',
                fieldname: 'repo_url',
                label: __('Repository URL'),
                reqd: 1,
                description: 'e.g., https://github.com/user/repo.git'
            },
            {
                fieldtype: 'Data',
                fieldname: 'branch',
                label: __('Branch'),
                default: 'main',
                reqd: 1
            }
        ],
        primary_action_label: __('Clone'),
        primary_action: function (values) {
            frappe.call({
                method: 'rpanel.hosting.git_manager.clone_repository',
                args: {
                    website_name: frm.doc.name,
                    repo_url: values.repo_url,
                    branch: values.branch
                },
                callback: function (r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({ message: __('Repository cloned'), indicator: 'green' });
                        d.hide();
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({ title: __('Clone Failed'), message: r.message.error, indicator: 'red' });
                    }
                }
            });
        }
    });
    d.show();
}

// Deployment History Dialog
function show_deployment_history(frm) {
    frappe.call({
        method: 'rpanel.hosting.git_manager.get_deployment_history',
        args: { website_name: frm.doc.name },
        callback: function (r) {
            if (r.message && r.message.success) {
                let commits_html = '<div class="deployment-history">';

                r.message.commits.forEach(commit => {
                    commits_html += `
                        <div class="commit-item" style="padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">${commit.hash}</code>
                                    <strong style="margin-left: 10px;">${commit.message}</strong>
                                </div>
                                <button class="btn btn-xs btn-default" onclick="rollback_to_commit('${commit.hash}')">
                                    Rollback
                                </button>
                            </div>
                            <div style="margin-top: 5px; color: #666; font-size: 12px;">
                                ${commit.author} • ${commit.date}
                            </div>
                        </div>
                    `;
                });

                commits_html += '</div>';

                let d = new frappe.ui.Dialog({
                    title: __('Deployment History'),
                    fields: [{ fieldtype: 'HTML', fieldname: 'commits_html' }],
                    size: 'large'
                });

                d.fields_dict.commits_html.$wrapper.html(commits_html);

                window.rollback_to_commit = function (hash) {
                    frappe.confirm(
                        `Rollback to commit ${hash.substring(0, 7)}?`,
                        function () {
                            frappe.call({
                                method: 'rpanel.hosting.git_manager.rollback_deployment',
                                args: { website_name: frm.doc.name, commit_hash: hash },
                                callback: function (r) {
                                    if (r.message && r.message.success) {
                                        frappe.show_alert({ message: __('Rolled back successfully'), indicator: 'green' });
                                        d.hide();
                                    }
                                }
                            });
                        }
                    );
                };

                d.show();
            } else {
                frappe.msgprint({ title: __('Error'), message: r.message.error, indicator: 'red' });
            }
        }
    });
}

// Webhook Setup Dialog
function show_webhook_dialog(frm) {
    frappe.call({
        method: 'rpanel.hosting.git_manager.setup_webhook',
        args: { website_name: frm.doc.name },
        callback: function (r) {
            if (r.message && r.message.success) {
                let d = new frappe.ui.Dialog({
                    title: __('Webhook Configuration'),
                    fields: [
                        {
                            fieldtype: 'HTML',
                            fieldname: 'webhook_html'
                        }
                    ]
                });

                let html = `
                    <div style="padding: 10px;">
                        <h4>Webhook URL</h4>
                        <input type="text" class="form-control" value="${r.message.webhook_url}" readonly onclick="this.select()">
                        <p class="text-muted" style="margin-top: 5px;">Add this URL to your Git repository's webhook settings</p>
                        
                        <h4 style="margin-top: 20px;">Webhook Secret</h4>
                        <input type="text" class="form-control" value="${r.message.webhook_secret}" readonly onclick="this.select()">
                        <p class="text-muted" style="margin-top: 5px;">Use this secret to verify webhook requests</p>
                        
                        <div style="margin-top: 20px; padding: 10px; background: #e7f3ff; border-left: 4px solid #2196F3;">
                            <strong>GitHub Setup:</strong>
                            <ol style="margin: 10px 0 0 0;">
                                <li>Go to your repository settings</li>
                                <li>Click "Webhooks" → "Add webhook"</li>
                                <li>Paste the webhook URL</li>
                                <li>Set content type to "application/json"</li>
                                <li>Paste the secret</li>
                                <li>Select "Just the push event"</li>
                                <li>Click "Add webhook"</li>
                            </ol>
                        </div>
                    </div>
                `;

                d.fields_dict.webhook_html.$wrapper.html(html);
                d.show();
            }
        }
    });
}

// Log Viewer Dialog
function show_log_viewer(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Log Viewer - ') + frm.doc.domain,
        size: 'extra-large',
        fields: [
            {
                fieldtype: 'Select', fieldname: 'log_type', label: __('Log Type'),
                options: 'Nginx Access\nNginx Error\nPHP Error\nApplication', default: 'Nginx Access',
                onchange: function () { load_log_content(d, frm); }
            },
            { fieldtype: 'Column Break' },
            { fieldtype: 'Data', fieldname: 'search_term', label: __('Search'), placeholder: 'Search logs...' },
            { fieldtype: 'Section Break' },
            { fieldtype: 'HTML', fieldname: 'log_content' }
        ],
        primary_action_label: __('Refresh'),
        primary_action: function () { load_log_content(d, frm); }
    });

    load_log_content(d, frm);
    let refresh_interval = setInterval(function () {
        if (d.is_visible) load_log_content(d, frm, true);
        else clearInterval(refresh_interval);
    }, 5000);
    d.show();
}

function load_log_content(dialog, frm, silent = false) {
    let log_type_map = { 'Nginx Access': 'nginx_access', 'Nginx Error': 'nginx_error', 'PHP Error': 'php_error', 'Application': 'application' };
    let log_type = log_type_map[dialog.get_value('log_type')];
    let search_term = dialog.get_value('search_term');

    let method = 'rpanel.hosting.log_viewer.get_nginx_access_log';
    if (log_type === 'nginx_error') method = 'rpanel.hosting.log_viewer.get_nginx_error_log';
    else if (log_type === 'php_error') method = 'rpanel.hosting.log_viewer.get_php_error_log';
    else if (log_type === 'application') method = 'rpanel.hosting.log_viewer.get_application_log';

    frappe.call({
        method: method,
        args: { website_name: frm.doc.name, lines: 200 },
        callback: function (r) {
            if (r.message && r.message.success) {
                let html = '<div style="background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 12px; max-height: 500px; overflow-y: auto;">';
                if (r.message.lines && r.message.lines.length > 0) {
                    r.message.lines.forEach(line => {
                        let color = '#d4d4d4';
                        if (line.includes('ERROR') || line.includes('error')) color = '#f48771';
                        else if (line.includes('WARNING') || line.includes('warning')) color = '#dcdcaa';
                        html += `<div style="color: ${color}; margin-bottom: 2px;">${line.replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m]))}</div>`;
                    });
                } else html += '<div style="color: #888;">No log entries found</div>';
                html += '</div>';
                dialog.fields_dict.log_content.$wrapper.html(html);
                if (!silent) frappe.show_alert({ message: __('Log loaded'), indicator: 'green' });
            }
        }
    });
}
