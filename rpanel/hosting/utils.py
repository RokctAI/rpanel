import subprocess
import os
import crypt
import frappe

def run_certbot(domain, webroot):
    """Issues a certificate for the domain using webroot challenge"""
    try:
        # Ensure webroot exists
        if not os.path.exists(webroot):
            os.makedirs(webroot, exist_ok=True)

        cmd = [
            "sudo", "certbot", "certonly",
            "--webroot",
            "-w", webroot,
            "-d", domain,
            "-d", f"www.{domain}",
            "--non-interactive",
            "--agree-tos",
            "--email", f"admin@{domain}" # Or a central admin email? Using domain admin for now.
        ]

        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, "Certificate issued successfully."
    except subprocess.CalledProcessError as e:
        return False, f"Certbot failed: {e.stderr}"

def update_exim_config(domain, accounts):
    """
    Updates Exim4 configuration for a domain.
    accounts: list of dicts {'user': 'info', 'password': '...', 'forward_to': '...'}
    """
    try:
        settings = frappe.get_single("Hosting Settings")
        passwd_file = settings.exim_passwd_file or "/etc/exim4/passwd"
        virtual_dir = settings.exim_virtual_dir or "/etc/exim4/virtual"

        # 1. Update Passwd File
        # Format: user@domain:hashed_password

        current_lines = []
        if os.path.exists(passwd_file):
            with open(passwd_file, 'r') as f:
                current_lines = f.readlines()

        # Safe removal of existing entries for this domain
        new_lines = []
        for line in current_lines:
            if ":" in line:
                user_part = line.split(":")[0]
                if "@" in user_part:
                    user_domain = user_part.split("@")[-1]
                    if user_domain == domain:
                        # Skip this line as it belongs to the domain we are updating
                        continue
            new_lines.append(line)

        # Add new entries
        for acc in accounts:
            full_user = f"{acc['user']}@{domain}"
            # Generate Crypt Hash
            # Salt should be random.
            salt = crypt.mksalt(crypt.METHOD_SHA512)
            hashed = crypt.crypt(acc['password'], salt)
            new_lines.append(f"{full_user}:{hashed}\n")

        # Write back (requires sudo, so write to temp and move)
        temp_passwd = f"/tmp/exim_passwd_{domain}"
        with open(temp_passwd, "w") as f:
            f.writelines(new_lines)

        subprocess.run(["sudo", "mv", temp_passwd, passwd_file], check=True)
        subprocess.run(["sudo", "chown", "root:exim", passwd_file], check=False) # specific to distro
        subprocess.run(["sudo", "chmod", "640", passwd_file], check=False)

        # 2. Update Virtual Map (Aliases/Forwarding)
        # Usually /etc/exim4/virtual/domain file
        domain_file = os.path.join(virtual_dir, domain)

        # Ensure virtual dir exists
        if not os.path.exists(virtual_dir):
            subprocess.run(["sudo", "mkdir", "-p", virtual_dir], check=True)

        lines = []
        for acc in accounts:
            if acc.get('forward_to'):
                lines.append(f"{acc['user']}: {acc['forward_to']}\n")
            else:
                # Local delivery
                mail_path = f"/var/mail/vhosts/{domain}/{acc['user']}/"
                lines.append(f"{acc['user']}: {mail_path}\n")

                # Ensure Maildir exists
                if not os.path.exists(mail_path):
                    subprocess.run(["sudo", "mkdir", "-p", mail_path], check=True)
                    subprocess.run(["sudo", "chown", "-R", "exim:exim", mail_path], check=False) # User might be mail or exim

        temp_virtual = f"/tmp/exim_virtual_{domain}"
        with open(temp_virtual, "w") as f:
            f.writelines(lines)

        subprocess.run(["sudo", "mv", temp_virtual, domain_file], check=True)

        # 3. Reload
        subprocess.run(["sudo", "update-exim4.conf"], check=False) # Debian specific
        subprocess.run(["sudo", "systemctl", "reload", "exim4"], check=True)

        return True, "Email configuration updated."

    except Exception as e:
        return False, f"Email update failed: {e}"
