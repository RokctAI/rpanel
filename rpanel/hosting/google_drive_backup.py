# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


@frappe.whitelist()
def upload_to_google_drive(backup_name):
    """Upload backup file to Google Drive"""
    backup = frappe.get_doc('Site Backup', backup_name)
    settings = frappe.get_single('Hosting Settings')

    # Get Google Drive credentials
    credentials_file = settings.get('google_drive_credentials_file')
    folder_id = settings.get('google_drive_folder_id')

    if not credentials_file or not os.path.exists(credentials_file):
        return {'success': False, 'error': 'Google Drive credentials not configured'}

    try:
        # Authenticate
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )

        service = build('drive', 'v3', credentials=credentials)

        # Prepare file metadata
        file_metadata = {
            'name': os.path.basename(backup.file_path),
            'parents': [folder_id] if folder_id else []
        }

        # Upload file
        media = MediaFileUpload(backup.file_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        # Update backup record
        backup.db_set('google_drive_file_id', file.get('id'))
        backup.db_set('google_drive_link', file.get('webViewLink'))
        backup.db_set('cloud_storage', 'Google Drive')
        frappe.db.commit()

        return {
            'success': True,
            'file_id': file.get('id'),
            'link': file.get('webViewLink')
        }

    except Exception as e:
        frappe.log_error(f"Google Drive upload failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def list_google_drive_backups():
    """List all backups in Google Drive"""
    settings = frappe.get_single('Hosting Settings')
    credentials_file = settings.get('google_drive_credentials_file')
    folder_id = settings.get('google_drive_folder_id')

    if not credentials_file:
        return {'success': False, 'error': 'Google Drive not configured'}

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )

        service = build('drive', 'v3', credentials=credentials)

        # Query for backup files
        query = f"'{folder_id}' in parents" if folder_id else "name contains 'backup'"

        results = service.files().list(
            q=query,
            pageSize=100,
            fields="files(id, name, size, createdTime, webViewLink)"
        ).execute()

        files = results.get('files', [])

        return {'success': True, 'files': files}

    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def download_from_google_drive(file_id, destination_path):
    """Download backup from Google Drive"""
    settings = frappe.get_single('Hosting Settings')
    credentials_file = settings.get('google_drive_credentials_file')

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )

        service = build('drive', 'v3', credentials=credentials)

        # Download file
        request = service.files().get_media(fileId=file_id)

        with open(destination_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        return {'success': True, 'path': destination_path}

    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def delete_from_google_drive(file_id):
    """Delete backup from Google Drive"""
    settings = frappe.get_single('Hosting Settings')
    credentials_file = settings.get('google_drive_credentials_file')

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )

        service = build('drive', 'v3', credentials=credentials)
        service.files().delete(fileId=file_id).execute()

        return {'success': True}

    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def setup_google_drive():
    """Setup Google Drive integration"""
    settings = frappe.get_single('Hosting Settings')
    credentials_file = settings.get('google_drive_credentials_file')

    if not credentials_file or not os.path.exists(credentials_file):
        return {
            'success': False,
            'error': 'Please upload Google Drive service account credentials JSON file'
        }

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )

        service = build('drive', 'v3', credentials=credentials)

        # Create backup folder if not exists
        folder_metadata = {
            'name': 'ROKCT Backups',
            'mimeType': 'application/vnd.google-apps.folder'
        }

        folder = service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder.get('id')

        # Save folder ID
        settings.db_set('google_drive_folder_id', folder_id)
        frappe.db.commit()

        return {
            'success': True,
            'folder_id': folder_id,
            'message': 'Google Drive configured successfully'
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}
