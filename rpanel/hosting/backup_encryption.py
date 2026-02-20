# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

"""
Backup Encryption Manager

Handles GPG encryption/decryption of backups before uploading to cloud storage.
"""

import frappe
import gnupg
import os


class BackupEncryptionManager:
    """Manages GPG encryption for backups"""

    def __init__(self):
        self.gpg_home = os.path.expanduser('~/.gnupg')
        self.gpg = gnupg.GPG(gnupghome=self.gpg_home)

    def generate_encryption_key(self, email="backup@rpanel.local", name="RPanel Backup"):
        """
        Generate a new GPG key pair for backup encryption

        Args:
            email: Email for the key
            name: Name for the key

        Returns:
            dict: Key information including fingerprint
        """
        # Generate key
        input_data = self.gpg.gen_key_input(
            name_real=name,
            name_email=email,
            key_type='RSA',
            key_length=4096,
            passphrase=''  # No passphrase for automated backups
        )

        key = self.gpg.gen_key(input_data)

        if not key:
            frappe.throw("Failed to generate encryption key")

        # Get key details
        keys = self.gpg.list_keys()
        key_info = next((k for k in keys if k['fingerprint'] == str(key)), None)

        if not key_info:
            frappe.throw("Generated key not found")

        # Update Security Settings
        settings = frappe.get_single('Security Settings')
        settings.encryption_key_fingerprint = key_info['fingerprint']
        settings.last_key_rotation = frappe.utils.now()
        settings.save()

        return {
            'fingerprint': key_info['fingerprint'],
            'key_id': key_info['keyid'],
            'created': key_info['date'],
            'expires': key_info.get('expires', 'Never')
        }

    def encrypt_file(self, file_path, output_path=None):
        """
        Encrypt a file using GPG

        Args:
            file_path: Path to file to encrypt
            output_path: Path for encrypted file (optional)

        Returns:
            str: Path to encrypted file
        """
        if not os.path.exists(file_path):
            frappe.throw(f"File not found: {file_path}")

        # Get encryption key fingerprint
        settings = frappe.get_single('Security Settings')
        fingerprint = settings.encryption_key_fingerprint

        if not fingerprint:
            frappe.throw("No encryption key configured. Please generate a key first.")

        # Set output path
        if not output_path:
            output_path = f"{file_path}.gpg"

        # Encrypt file
        with open(file_path, 'rb') as f:
            encrypted = self.gpg.encrypt_file(
                f,
                recipients=[fingerprint],
                output=output_path,
                always_trust=True
            )

        if not encrypted.ok:
            frappe.throw(f"Encryption failed: {encrypted.status}")

        return output_path

    def decrypt_file(self, encrypted_file_path, output_path=None):
        """
        Decrypt a GPG-encrypted file

        Args:
            encrypted_file_path: Path to encrypted file
            output_path: Path for decrypted file (optional)

        Returns:
            str: Path to decrypted file
        """
        if not os.path.exists(encrypted_file_path):
            frappe.throw(f"Encrypted file not found: {encrypted_file_path}")

        # Set output path
        if not output_path:
            output_path = encrypted_file_path.replace('.gpg', '')

        # Decrypt file
        with open(encrypted_file_path, 'rb') as f:
            decrypted = self.gpg.decrypt_file(f, output=output_path)

        if not decrypted.ok:
            frappe.throw(f"Decryption failed: {decrypted.status}")

        return output_path

    def export_public_key(self, fingerprint=None):
        """
        Export public key for backup/sharing

        Args:
            fingerprint: Key fingerprint (uses configured key if not provided)

        Returns:
            str: ASCII-armored public key
        """
        if not fingerprint:
            settings = frappe.get_single('Security Settings')
            fingerprint = settings.encryption_key_fingerprint

        if not fingerprint:
            frappe.throw("No encryption key configured")

        public_key = self.gpg.export_keys(fingerprint)

        if not public_key:
            frappe.throw("Failed to export public key")

        return public_key

    def export_private_key(self, fingerprint=None):
        """
        Export private key for backup (KEEP SECURE!)

        Args:
            fingerprint: Key fingerprint (uses configured key if not provided)

        Returns:
            str: ASCII-armored private key
        """
        if not fingerprint:
            settings = frappe.get_single('Security Settings')
            fingerprint = settings.encryption_key_fingerprint

        if not fingerprint:
            frappe.throw("No encryption key configured")

        private_key = self.gpg.export_keys(fingerprint, secret=True)

        if not private_key:
            frappe.throw("Failed to export private key")

        return private_key

    def import_key(self, key_data):
        """
        Import a GPG key

        Args:
            key_data: ASCII-armored key data

        Returns:
            dict: Import result
        """
        result = self.gpg.import_keys(key_data)

        if not result.fingerprints:
            frappe.throw("Failed to import key")

        return {
            'fingerprints': result.fingerprints,
            'count': result.count,
            'imported': result.imported
        }


# Convenience functions for use in other modules

def encrypt_backup(backup_file_path):
    """
    Encrypt a backup file

    Args:
        backup_file_path: Path to backup file

    Returns:
        str: Path to encrypted file
    """
    manager = BackupEncryptionManager()
    return manager.encrypt_file(backup_file_path)


def decrypt_backup(encrypted_file_path):
    """
    Decrypt an encrypted backup file

    Args:
        encrypted_file_path: Path to encrypted file

    Returns:
        str: Path to decrypted file
    """
    manager = BackupEncryptionManager()
    return manager.decrypt_file(encrypted_file_path)


@frappe.whitelist()
def generate_encryption_key():
    """Generate a new encryption key (whitelisted for UI)"""
    manager = BackupEncryptionManager()
    return manager.generate_encryption_key()


@frappe.whitelist()
def download_public_key():
    """Download public key (whitelisted for UI)"""
    manager = BackupEncryptionManager()
    public_key = manager.export_public_key()

    frappe.response['filename'] = 'rpanel_backup_public_key.asc'
    frappe.response['filecontent'] = public_key
    frappe.response['type'] = 'download'


@frappe.whitelist()
def download_private_key():
    """Download private key (whitelisted for UI) - KEEP SECURE!"""
    # Only allow System Managers
    if 'System Manager' not in frappe.get_roles():
        frappe.throw("Not permitted")

    manager = BackupEncryptionManager()
    private_key = manager.export_private_key()

    frappe.response['filename'] = 'rpanel_backup_private_key.asc'
    frappe.response['filecontent'] = private_key
    frappe.response['type'] = 'download'

    # Log this action
    frappe.log_error(
        f"Private key downloaded by {frappe.session.user}",
        "Security: Private Key Download"
    )
