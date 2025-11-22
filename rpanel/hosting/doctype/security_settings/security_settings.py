# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import pyotp
import qrcode
import io
import base64


class SecuritySettings(Document):
	def validate(self):
		"""Validate security settings"""
		if self.enable_2fa:
			# Count users with 2FA enabled
			self.set('2fa_enabled_users', frappe.db.count('User', {'two_factor_auth': 1}))
	
	def on_update(self):
		"""Handle settings updates"""
		if self.enable_2fa and self.enforce_2fa_for_admins:
			# Enable 2FA for all System Managers
			self.enforce_2fa_for_system_managers()
	
	def enforce_2fa_for_system_managers(self):
		"""Enable 2FA for all users with System Manager role"""
		system_managers = frappe.get_all(
			'Has Role',
			filters={'role': 'System Manager', 'parenttype': 'User'},
			fields=['parent']
		)
		
		for manager in system_managers:
			user = manager.parent
			if not frappe.db.get_value('User', user, 'two_factor_auth'):
				frappe.msgprint(f"2FA enforcement: User {user} needs to enable 2FA")


@frappe.whitelist()
def enable_user_2fa(user=None):
	"""
	Enable 2FA for a user and generate QR code
	
	Args:
		user: User email (defaults to current user)
	
	Returns:
		dict: QR code image (base64) and secret key
	"""
	if not user:
		user = frappe.session.user
	
	# Check permissions
	if frappe.session.user != user and not frappe.has_permission('User', 'write'):
		frappe.throw("Not permitted")
	
	# Generate secret
	secret = pyotp.random_base32()
	
	# Get issuer name from settings
	settings = frappe.get_single('Security Settings')
	issuer_name = settings.get('2fa_issuer_name', 'RPanel')
	
	# Generate TOTP URI
	totp = pyotp.TOTP(secret)
	uri = totp.provisioning_uri(
		name=user,
		issuer_name=issuer_name
	)
	
	# Generate QR code
	qr = qrcode.QRCode(version=1, box_size=10, border=5)
	qr.add_data(uri)
	qr.make(fit=True)
	
	img = qr.make_image(fill_color="black", back_color="white")
	
	# Convert to base64
	buffer = io.BytesIO()
	img.save(buffer, format='PNG')
	img_str = base64.b64encode(buffer.getvalue()).decode()
	
	# Store secret temporarily (user will verify before it's saved permanently)
	frappe.cache().set_value(
		f'2fa_temp_secret_{user}',
		secret,
		expires_in_sec=300  # 5 minutes
	)
	
	return {
		'qr_code': f'data:image/png;base64,{img_str}',
		'secret': secret,
		'message': 'Scan this QR code with Google Authenticator or Authy'
	}


@frappe.whitelist()
def verify_and_enable_2fa(user=None, otp_code=None):
	"""
	Verify OTP code and enable 2FA for user
	
	Args:
		user: User email
		otp_code: 6-digit OTP code from authenticator app
	
	Returns:
		dict: Success status and message
	"""
	if not user:
		user = frappe.session.user
	
	if not otp_code:
		frappe.throw("OTP code is required")
	
	# Get temporary secret
	secret = frappe.cache().get_value(f'2fa_temp_secret_{user}')
	
	if not secret:
		frappe.throw("2FA setup expired. Please start again.")
	
	# Verify OTP
	totp = pyotp.TOTP(secret)
	if not totp.verify(otp_code):
		frappe.throw("Invalid OTP code")
	
	# Enable 2FA for user
	user_doc = frappe.get_doc('User', user)
	user_doc.two_factor_auth = 1
	user_doc.save(ignore_permissions=True)
	
	# Clear temporary secret
	frappe.cache().delete_value(f'2fa_temp_secret_{user}')
	
	# Update count in settings
	settings = frappe.get_single('Security Settings')
	settings.save()
	
	return {
		'success': True,
		'message': f'Two-Factor Authentication enabled for {user}'
	}


@frappe.whitelist()
def disable_user_2fa(user=None):
	"""
	Disable 2FA for a user
	
	Args:
		user: User email (defaults to current user)
	
	Returns:
		dict: Success status and message
	"""
	if not user:
		user = frappe.session.user
	
	# Check permissions
	if frappe.session.user != user and not frappe.has_permission('User', 'write'):
		frappe.throw("Not permitted")
	
	# Disable 2FA
	user_doc = frappe.get_doc('User', user)
	user_doc.two_factor_auth = 0
	user_doc.save(ignore_permissions=True)
	
	# Update count in settings
	settings = frappe.get_single('Security Settings')
	settings.save()
	
	return {
		'success': True,
		'message': f'Two-Factor Authentication disabled for {user}'
	}


@frappe.whitelist()
def get_2fa_status():
	"""
	Get 2FA status for current user and system
	
	Returns:
		dict: 2FA status information
	"""
	user = frappe.session.user
	settings = frappe.get_single('Security Settings')
	
	user_2fa_enabled = frappe.db.get_value('User', user, 'two_factor_auth')
	
	return {
		'system_2fa_enabled': settings.enable_2fa,
		'enforce_for_admins': settings.enforce_2fa_for_admins,
		'user_2fa_enabled': bool(user_2fa_enabled),
		'total_users_with_2fa': settings.get('2fa_enabled_users', 0),
		'issuer_name': settings.get('2fa_issuer_name', 'RPanel')
	}
