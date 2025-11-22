# Copyright (c) 2025, Rendani Sinyage and contributors
# For license information, please see license.txt

import frappe
import os
import subprocess
import shlex
from datetime import datetime
import hmac
import hashlib

@frappe.whitelist()
def clone_repository(website_name, repo_url, branch='main', deploy_key=None):
    """Clone a Git repository to website directory"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        # Check if directory is empty or doesn't exist
        if os.path.exists(website.site_path) and os.listdir(website.site_path):
            return {'success': False, 'error': 'Site directory is not empty'}
        
        # Ensure directory exists
        os.makedirs(website.site_path, exist_ok=True)
        
        # Clone repository
        cmd = f"git clone -b {branch} {repo_url} {website.site_path}"
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            # Store Git info in website
            website.db_set('git_repository', repo_url)
            website.db_set('git_branch', branch)
            website.db_set('last_deployment', datetime.now())
            website.db_set('deployment_status', 'Success')
            frappe.db.commit()
            
            return {'success': True, 'message': 'Repository cloned successfully'}
        else:
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        frappe.log_error(f"Git clone failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def pull_latest(website_name):
    """Pull latest changes from Git repository"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        if not os.path.exists(os.path.join(website.site_path, '.git')):
            return {'success': False, 'error': 'Not a Git repository'}
        
        # Pull latest changes
        cmd = f"git -C {website.site_path} pull origin {website.git_branch or 'main'}"
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            website.db_set('last_deployment', datetime.now())
            website.db_set('deployment_status', 'Success')
            frappe.db.commit()
            
            return {'success': True, 'message': 'Pulled latest changes', 'output': result.stdout}
        else:
            website.db_set('deployment_status', 'Failed')
            frappe.db.commit()
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        frappe.log_error(f"Git pull failed: {str(e)}")
        website.db_set('deployment_status', 'Failed')
        frappe.db.commit()
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def switch_branch(website_name, branch):
    """Switch to a different Git branch"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        if not os.path.exists(os.path.join(website.site_path, '.git')):
            return {'success': False, 'error': 'Not a Git repository'}
        
        # Fetch all branches
        subprocess.run(
            shlex.split(f"git -C {website.site_path} fetch --all"),
            capture_output=True,
            timeout=60
        )
        
        # Switch branch
        cmd = f"git -C {website.site_path} checkout {branch}"
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            website.db_set('git_branch', branch)
            website.db_set('last_deployment', datetime.now())
            frappe.db.commit()
            
            return {'success': True, 'message': f'Switched to branch {branch}'}
        else:
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        frappe.log_error(f"Git branch switch failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_branches(website_name):
    """Get list of available Git branches"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        if not os.path.exists(os.path.join(website.site_path, '.git')):
            return {'success': False, 'error': 'Not a Git repository'}
        
        # Get branches
        cmd = f"git -C {website.site_path} branch -r"
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            branches = [b.strip().replace('origin/', '') for b in result.stdout.split('\n') if b.strip() and 'HEAD' not in b]
            return {'success': True, 'branches': branches}
        else:
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_deployment_history(website_name, limit=10):
    """Get deployment history from Git log"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        if not os.path.exists(os.path.join(website.site_path, '.git')):
            return {'success': False, 'error': 'Not a Git repository'}
        
        # Get Git log
        cmd = f"git -C {website.site_path} log --pretty=format:'%H|%an|%ae|%ad|%s' --date=iso -n {limit}"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            commits = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split('|')
                    if len(parts) == 5:
                        commits.append({
                            'hash': parts[0],
                            'author': parts[1],
                            'email': parts[2],
                            'date': parts[3],
                            'message': parts[4]
                        })
            
            return {'success': True, 'commits': commits}
        else:
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def rollback_deployment(website_name, commit_hash):
    """Rollback to a specific commit"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        if not os.path.exists(os.path.join(website.site_path, '.git')):
            return {'success': False, 'error': 'Not a Git repository'}
        
        # Reset to commit
        cmd = f"git -C {website.site_path} reset --hard {commit_hash}"
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            website.db_set('last_deployment', datetime.now())
            website.db_set('deployment_status', 'Rolled Back')
            frappe.db.commit()
            
            return {'success': True, 'message': f'Rolled back to {commit_hash[:7]}'}
        else:
            return {'success': False, 'error': result.stderr}
            
    except Exception as e:
        frappe.log_error(f"Git rollback failed: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def setup_webhook(website_name):
    """Generate webhook URL and secret for auto-deployment"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    # Generate webhook secret
    import secrets
    webhook_secret = secrets.token_urlsafe(32)
    
    website.db_set('webhook_secret', webhook_secret)
    frappe.db.commit()
    
    # Generate webhook URL
    site_url = frappe.utils.get_url()
    webhook_url = f"{site_url}/api/method/rpanel.hosting.git_manager.handle_webhook?website={website_name}"
    
    return {
        'success': True,
        'webhook_url': webhook_url,
        'webhook_secret': webhook_secret
    }


@frappe.whitelist(allow_guest=True)
def handle_webhook(**kwargs):
    """Handle Git webhook for auto-deployment"""
    try:
        # Get website name from query params
        website_name = frappe.request.args.get('website')
        if not website_name:
            frappe.throw("Website parameter missing")
        
        website = frappe.get_doc('Hosted Website', website_name)
        
        # Verify webhook signature
        signature = frappe.request.headers.get('X-Hub-Signature-256') or frappe.request.headers.get('X-Gitlab-Token')
        
        if website.webhook_secret:
            # Verify signature for GitHub
            if signature and signature.startswith('sha256='):
                payload = frappe.request.get_data()
                expected_signature = 'sha256=' + hmac.new(
                    website.webhook_secret.encode(),
                    payload,
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(signature, expected_signature):
                    frappe.throw("Invalid webhook signature")
        
        # Pull latest changes
        result = pull_latest(website_name)
        
        if result.get('success'):
            return {'status': 'success', 'message': 'Deployment triggered'}
        else:
            return {'status': 'error', 'message': result.get('error')}
            
    except Exception as e:
        frappe.log_error(f"Webhook handling failed: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@frappe.whitelist()
def get_git_status(website_name):
    """Get current Git status"""
    website = frappe.get_doc('Hosted Website', website_name)
    
    try:
        if not os.path.exists(os.path.join(website.site_path, '.git')):
            return {'success': False, 'error': 'Not a Git repository'}
        
        # Get status
        cmd = f"git -C {website.site_path} status --porcelain"
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Get current branch
        branch_cmd = f"git -C {website.site_path} rev-parse --abbrev-ref HEAD"
        branch_result = subprocess.run(
            shlex.split(branch_cmd),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Get latest commit
        commit_cmd = f"git -C {website.site_path} log -1 --pretty=format:'%H|%s|%an|%ad' --date=short"
        commit_result = subprocess.run(
            commit_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        status = {
            'success': True,
            'is_clean': len(result.stdout.strip()) == 0,
            'current_branch': branch_result.stdout.strip(),
            'changes': result.stdout.strip().split('\n') if result.stdout.strip() else []
        }
        
        if commit_result.stdout.strip():
            parts = commit_result.stdout.strip().split('|')
            if len(parts) == 4:
                status['latest_commit'] = {
                    'hash': parts[0][:7],
                    'message': parts[1],
                    'author': parts[2],
                    'date': parts[3]
                }
        
        return status
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
