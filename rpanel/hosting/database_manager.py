# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import frappe
import subprocess
import shlex
import json

@frappe.whitelist()
def execute_query(database_name, query):
    """Execute SQL query"""
    # Security: Only allow SELECT queries for safety
    if not query.strip().upper().startswith('SELECT'):
        return {'success': False, 'error': 'Only SELECT queries are allowed'}
    
    try:
        cmd = f"mysql -u root -e \"{query}\" {database_name} --json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout) if result.stdout else []
            return {'success': True, 'data': data}
        else:
            return {'success': False, 'error': result.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_tables(database_name):
    """Get list of tables in database"""
    try:
        cmd = f"mysql -u root -e 'SHOW TABLES' {database_name} --json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            tables = json.loads(result.stdout)
            return {'success': True, 'tables': tables}
        else:
            return {'success': False, 'error': result.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_table_structure(database_name, table_name):
    """Get table structure"""
    try:
        cmd = f"mysql -u root -e 'DESCRIBE {table_name}' {database_name} --json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            structure = json.loads(result.stdout)
            return {'success': True, 'structure': structure}
        else:
            return {'success': False, 'error': result.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def export_database(database_name, export_format='sql'):
    """Export database"""
    try:
        export_file = f"/tmp/{database_name}_export.{export_format}"
        
        if export_format == 'sql':
            cmd = f"mysqldump -u root {database_name} > {export_file}"
        elif export_format == 'csv':
            # Export all tables to CSV
            cmd = f"mysql -u root -e 'SELECT * FROM table_name' {database_name} > {export_file}"
        
        subprocess.run(cmd, shell=True, check=True)
        
        return {'success': True, 'file_path': export_file}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def import_database(database_name, import_file):
    """Import database from SQL file"""
    try:
        cmd = f"mysql -u root {database_name} < {import_file}"
        subprocess.run(cmd, shell=True, check=True)
        
        return {'success': True, 'message': 'Database imported'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def optimize_database(database_name):
    """Optimize all tables in database"""
    try:
        cmd = f"mysqlcheck -u root --optimize {database_name}"
        result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
        
        return {'success': True, 'output': result.stdout}
    except Exception as e:
        return {'success': False, 'error': str(e)}
