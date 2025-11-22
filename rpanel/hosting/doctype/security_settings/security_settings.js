
// Generate Key Button (only if no key or user wants to rotate)
frm.add_custom_button(__('Generate New Key'), function () {
    let msg = __('Are you sure you want to generate a new encryption key?');
    if (frm.doc.encryption_key_fingerprint) {
        msg += '<br><br>' + __('<b>WARNING:</b> This will replace the existing key. You should backup your old private key first to decrypt old backups.');
    }

    frappe.confirm(msg, function () {
        frappe.call({
            method: 'rpanel.hosting.backup_encryption.generate_encryption_key',
            freeze: true,
            freeze_message: __('Generating 4096-bit RSA key... This may take a moment.'),
            callback: function (r) {
                if (!r.exc) {
                    frappe.msgprint(__('New encryption key generated successfully'));
                    frm.reload_doc();
                }
            }
        });
    });
}, __('Encryption Keys'));

// Download Public Key
if (frm.doc.encryption_key_fingerprint) {
    frm.add_custom_button(__('Download Public Key'), function () {
        window.open('/api/method/rpanel.hosting.backup_encryption.download_public_key');
    }, __('Encryption Keys'));

    // Download Private Key (with warning)
    frm.add_custom_button(__('Download Private Key'), function () {
        frappe.confirm(
            __('<b>WARNING:</b> You are about to download the private encryption key. Store this securely! If you lose this key, you will NOT be able to decrypt your backups.<br><br>Do you want to proceed?'),
            function () {
                window.open('/api/method/rpanel.hosting.backup_encryption.download_private_key');
            }
        );
    }, __('Encryption Keys'));
}
        }
    },

enable_backup_encryption: function (frm) {
    if (frm.doc.enable_backup_encryption && !frm.doc.encryption_key_fingerprint) {
        frappe.msgprint({
            title: __('Setup Required'),
            message: __('Please generate an encryption key to enable backup encryption.'),
            indicator: 'orange'
        });
    }
}
});
