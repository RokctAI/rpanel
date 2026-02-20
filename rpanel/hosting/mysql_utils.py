"""
Secure MySQL/MariaDB command execution utilities.

Prevents password exposure in process lists by using temporary config files.
"""

import os
import tempfile
import subprocess
from typing import Optional, List, Dict, Any
import frappe


def run_mysql_command(
    sql: str,
    database: Optional[str] = None,
    user: str = "root",
    password: Optional[str] = None,
    host: str = "localhost",
    as_sudo: bool = True
) -> subprocess.CompletedProcess:
    """
    Execute a MySQL command securely without exposing passwords.
    
    Args:
        sql: SQL statement to execute
        database: Database name (optional)
        user: MySQL user (default: root)
        password: MySQL password (passed securely via config file)
        host: MySQL host (default: localhost)
        as_sudo: Run with sudo privileges (default: True)
    
    Returns:
        subprocess.CompletedProcess instance
    
    Example:
        run_mysql_command("CREATE DATABASE mydb", user="admin", password="secret")
    """
    config_file = None
    try:
        # Create temporary config file with password
        config_file = _create_mysql_config(user, password, host)
        
        # Build command
        cmd = []
        if as_sudo:
            cmd.append("sudo")
        
        cmd.extend(["mysql", f"--defaults-extra-file={config_file}"])
        
        if database:
            cmd.append(database)
        
        cmd.extend(["-e", sql])
        
        # Execute command (password NOT visible in process list)
        return subprocess.run(cmd, check=True, capture_output=True, text=True)
        
    finally:
        # Always clean up the config file
        if config_file and os.path.exists(config_file):
            os.remove(config_file)


def run_mysqldump(
    database: str,
    output_file: str,
    user: str = "root",
    password: Optional[str] = None,
    host: str = "localhost",
    tables: Optional[List[str]] = None,
    as_sudo: bool = False
) -> subprocess.CompletedProcess:
    """
    Execute mysqldump securely without exposing passwords.
    
    Args:
        database: Database to dump
        output_file: Path to output SQL file
        user: MySQL user (default: root)
        password: MySQL password (passed securely)
        host: MySQL host (default: localhost)
        tables: Specific tables to dump (optional)
        as_sudo: Run with sudo (default: False for mysqldump)
    
    Returns:
        subprocess.CompletedProcess instance
    
    Example:
        run_mysqldump("mydb", "/backups/mydb.sql", user="dbuser", password="secret")
    """
    config_file = None
    try:
        # Create temporary config file
        config_file = _create_mysql_config(user, password, host)
        
        # Build command
        cmd = []
        if as_sudo:
            cmd.append("sudo")
        
        cmd.extend(["mysqldump", f"--defaults-extra-file={config_file}", database])
        
        if tables:
            cmd.extend(tables)
        
        # Execute and redirect to file
        with open(output_file, 'w') as f:
            return subprocess.run(cmd, stdout=f, check=True, text=True)
        
    finally:
        if config_file and os.path.exists(config_file):
            os.remove(config_file)


def run_mysql_restore(
    database: str,
    input_file: str,
    user: str = "root",
    password: Optional[str] = None,
    host: str = "localhost",
    as_sudo: bool = False
) -> subprocess.CompletedProcess:
    """
    Restore a MySQL database from SQL file securely.
    
    Args:
        database: Target database
        input_file: Path to SQL file to import
        user: MySQL user (default: root)
        password: MySQL password (passed securely)
        host: MySQL host (default: localhost)
        as_sudo: Run with sudo (default: False)
    
    Returns:
        subprocess.CompletedProcess instance
    
    Example:
        run_mysql_restore("mydb", "/backups/mydb.sql", user="dbuser", password="secret")
    """
    config_file = None
    try:
        # Create temporary config file
        config_file = _create_mysql_config(user, password, host)
        
        # Build command
        cmd = []
        if as_sudo:
            cmd.append("sudo")
        
        cmd.extend(["mysql", f"--defaults-extra-file={config_file}", database])
        
        # Execute with input redirection
        with open(input_file, 'r') as f:
            return subprocess.run(cmd, stdin=f, check=True, text=True)
        
    finally:
        if config_file and os.path.exists(config_file):
            os.remove(config_file)


def _create_mysql_config(user: str, password: Optional[str], host: str = "localhost") -> str:
    """
    Create a temporary MySQL config file with credentials.
    
    The file has restrictive permissions (0600) so only the owner can read it.
    
    Args:
        user: MySQL username
        password: MySQL password
        host: MySQL host
    
    Returns:
        Path to temporary config file
    """
    # Create config content
    config_content = f"""[client]
user={user}
host={host}
"""
    if password:
        config_content += f"password={password}\n"
    
    # Create temporary file
    fd, config_path = tempfile.mkstemp(suffix='.cnf', prefix='mysql_', text=True)
    
    try:
        # Write config to file
        with os.fdopen(fd, 'w') as f:
            f.write(config_content)
        
        # Set restrictive permissions (owner read/write only)
        os.chmod(config_path, 0o600)
        
        return config_path
        
    except Exception:
        # Clean up on error
        if os.path.exists(config_path):
            os.remove(config_path)
        raise


def get_db_password_from_config() -> str:
    """
    Get MariaDB root password from Frappe's common_site_config.json.
    
    Returns:
        Database root password
    """
    import json
    
    try:
        config_path = os.path.join(frappe.utils.get_bench_path(), 'sites', 'common_site_config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        return config.get('db_password') or config.get('root_password', '')
    except Exception as e:
        frappe.log_error(f"Could not read MariaDB password from config: {str(e)}")
        return ''
