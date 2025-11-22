# Copyright (c) 2025, ROKCT Holdings and contributors
# For license information, please see license.txt

import frappe
import os
import json
import base64
from pathlib import Path
from frappe.utils import get_files_path, cstr
import mimetypes

@frappe.whitelist()
def get_file_list(website_name, path=""):
    """Get list of files and directories for a website"""
    doc = frappe.get_doc('Hosted Website', website_name)
    
    # Security: Ensure path doesn't escape site_path
    base_path = doc.site_path
    if not base_path or not os.path.exists(base_path):
        frappe.throw(f"Site path does not exist: {base_path}")
    
    # Construct full path
    full_path = os.path.join(base_path, path.lstrip('/'))
    
    # Security check: ensure we're still within site_path
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_path)):
        frappe.throw("Invalid path - access denied")
    
    if not os.path.exists(full_path):
        frappe.throw(f"Path does not exist: {path}")
    
    items = []
    
    try:
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            relative_path = os.path.join(path, item)
            
            stat = os.stat(item_path)
            
            items.append({
                'name': item,
                'path': relative_path,
                'is_dir': os.path.isdir(item_path),
                'size': stat.st_size if not os.path.isdir(item_path) else 0,
                'modified': stat.st_mtime,
                'permissions': oct(stat.st_mode)[-3:]
            })
        
        # Sort: directories first, then files
        items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
        
        return {
            'current_path': path,
            'items': items,
            'base_path': base_path
        }
    
    except PermissionError:
        frappe.throw("Permission denied to access this directory")

@frappe.whitelist()
def download_file(website_name, file_path):
    """Download a file from the website directory"""
    doc = frappe.get_doc('Hosted Website', website_name)
    
    base_path = doc.site_path
    full_path = os.path.join(base_path, file_path.lstrip('/'))
    
    # Security check
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_path)):
        frappe.throw("Invalid path - access denied")
    
    if not os.path.exists(full_path) or os.path.isdir(full_path):
        frappe.throw("File not found")
    
    try:
        with open(full_path, 'rb') as f:
            content = f.read()
        
        filename = os.path.basename(full_path)
        
        frappe.local.response.filename = filename
        frappe.local.response.filecontent = content
        frappe.local.response.type = "download"
        
    except PermissionError:
        frappe.throw("Permission denied to read this file")

@frappe.whitelist()
def upload_file(website_name, path, filename, filedata):
    """Upload a file to the website directory"""
    doc = frappe.get_doc('Hosted Website', website_name)
    
    base_path = doc.site_path
    target_dir = os.path.join(base_path, path.lstrip('/'))
    
    # Security check
    if not os.path.abspath(target_dir).startswith(os.path.abspath(base_path)):
        frappe.throw("Invalid path - access denied")
    
    if not os.path.exists(target_dir):
        frappe.throw("Target directory does not exist")
    
    target_file = os.path.join(target_dir, filename)
    
    try:
        # Decode base64 file data
        file_content = base64.b64decode(filedata)
        
        # Write file
        with open(target_file, 'wb') as f:
            f.write(file_content)
        
        # Set permissions
        os.chmod(target_file, 0o644)
        
        return {
            'success': True,
            'message': f'File {filename} uploaded successfully',
            'path': os.path.join(path, filename)
        }
    
    except Exception as e:
        frappe.log_error(f"File upload failed: {str(e)}")
        frappe.throw(f"Upload failed: {str(e)}")

@frappe.whitelist()
def delete_file(website_name, file_path):
    """Delete a file or directory"""
    doc = frappe.get_doc('Hosted Website', website_name)
    
    base_path = doc.site_path
    full_path = os.path.join(base_path, file_path.lstrip('/'))
    
    # Security check
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_path)):
        frappe.throw("Invalid path - access denied")
    
    if not os.path.exists(full_path):
        frappe.throw("File or directory not found")
    
    try:
        import shutil
        
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        
        return {
            'success': True,
            'message': f'Deleted successfully'
        }
    
    except Exception as e:
        frappe.log_error(f"Delete failed: {str(e)}")
        frappe.throw(f"Delete failed: {str(e)}")

@frappe.whitelist()
def create_directory(website_name, path, dirname):
    """Create a new directory"""
    doc = frappe.get_doc('Hosted Website', website_name)
    
    base_path = doc.site_path
    parent_dir = os.path.join(base_path, path.lstrip('/'))
    new_dir = os.path.join(parent_dir, dirname)
    
    # Security check
    if not os.path.abspath(new_dir).startswith(os.path.abspath(base_path)):
        frappe.throw("Invalid path - access denied")
    
    if os.path.exists(new_dir):
        frappe.throw("Directory already exists")
    
    try:
        os.makedirs(new_dir)
        os.chmod(new_dir, 0o755)
        
        return {
            'success': True,
            'message': f'Directory {dirname} created successfully',
            'path': os.path.join(path, dirname)
        }
    
    except Exception as e:
        frappe.log_error(f"Create directory failed: {str(e)}")
        frappe.throw(f"Create directory failed: {str(e)}")

@frappe.whitelist()
def rename_file(website_name, old_path, new_name):
    """Rename a file or directory"""
    doc = frappe.get_doc('Hosted Website', website_name)
    
    base_path = doc.site_path
    old_full_path = os.path.join(base_path, old_path.lstrip('/'))
    
    # Get parent directory
    parent_dir = os.path.dirname(old_full_path)
    new_full_path = os.path.join(parent_dir, new_name)
    
    # Security checks
    if not os.path.abspath(old_full_path).startswith(os.path.abspath(base_path)):
        frappe.throw("Invalid path - access denied")
    
    if not os.path.abspath(new_full_path).startswith(os.path.abspath(base_path)):
        frappe.throw("Invalid path - access denied")
    
    if not os.path.exists(old_full_path):
        frappe.throw("File or directory not found")
    
    if os.path.exists(new_full_path):
        frappe.throw("A file or directory with that name already exists")
    
    try:
        os.rename(old_full_path, new_full_path)
        
        return {
            'success': True,
            'message': f'Renamed successfully',
            'new_path': os.path.join(os.path.dirname(old_path), new_name)
        }
    
    except Exception as e:
        frappe.log_error(f"Rename failed: {str(e)}")
        frappe.throw(f"Rename failed: {str(e)}")

@frappe.whitelist()
def read_file(website_name, file_path):
    """Read file content (for text files)"""
    doc = frappe.get_doc('Hosted Website', website_name)
    
    base_path = doc.site_path
    full_path = os.path.join(base_path, file_path.lstrip('/'))
    
    # Security check
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_path)):
        frappe.throw("Invalid path - access denied")
    
    if not os.path.exists(full_path) or os.path.isdir(full_path):
        frappe.throw("File not found")
    
    # Check file size (limit to 1MB for editing)
    if os.path.getsize(full_path) > 1024 * 1024:
        frappe.throw("File too large to edit (max 1MB)")
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            'content': content,
            'path': file_path,
            'size': os.path.getsize(full_path)
        }
    
    except UnicodeDecodeError:
        frappe.throw("File is not a text file")
    except Exception as e:
        frappe.log_error(f"Read file failed: {str(e)}")
        frappe.throw(f"Read file failed: {str(e)}")

@frappe.whitelist()
def save_file(website_name, file_path, content):
    """Save file content (for text files)"""
    doc = frappe.get_doc('Hosted Website', website_name)
    
    base_path = doc.site_path
    full_path = os.path.join(base_path, file_path.lstrip('/'))
    
    # Security check
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_path)):
        frappe.throw("Invalid path - access denied")
    
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            'success': True,
            'message': 'File saved successfully'
        }
    
    except Exception as e:
        frappe.log_error(f"Save file failed: {str(e)}")
        frappe.throw(f"Save file failed: {str(e)}")
