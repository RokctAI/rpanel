# Copyright (c) 2025, Rokct Holdings and contributors
# For license information, please see license.txt

import sys
import re
import os
import frappe
import subprocess
import json


@frappe.whitelist()
def execute_query(database_name: str, query: str) -> dict:
    """Execute SQL query"""
    # Security: Only allow SELECT queries for safety
    sys.stderr.write(
        f"[TRACE] execute_query trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    frappe.only_for("System Manager")

    stripped = query.strip()
    if not stripped.upper().startswith("SELECT"):
        return {"success": False, "error": "Only SELECT queries are allowed"}

    # Security: a bare ";" lets psql/mysql chain a second statement past the
    # SELECT-only prefix check (e.g. "SELECT 1; DROP TABLE x"). Reject any
    # semicolon except a single optional trailing one.
    if ";" in stripped.rstrip(";"):
        return {"success": False, "error": "Only a single SELECT statement is allowed"}

    try:
        if frappe.db.db_type == "postgres":
            # Security: Use list to prevent command injection
            cmd = ["psql", "-d", database_name, "-c", query, "--json=auto"]
            result = subprocess.run(cmd, capture_output=True, text=True)
        else:
            # Security: Use list to prevent command injection
            cmd = ["mysql", "-u", "root", "-e", query, database_name, "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            data = json.loads(result.stdout) if result.stdout else []
            return {"success": True, "data": data}
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_tables(database_name: str) -> dict:
    """Get list of tables in database"""
    sys.stderr.write(
        f"[TRACE] get_tables trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        if frappe.db.db_type == "postgres":
            # Query for postgres tables
            query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            cmd = ["psql", "-d", database_name, "-c", query, "--json=auto"]
            result = subprocess.run(cmd, capture_output=True, text=True)
        else:
            # Security: Use list to prevent command injection
            cmd = ["mysql", "-u", "root", "-e", "SHOW TABLES", database_name, "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            tables = json.loads(result.stdout)
            return {"success": True, "tables": tables}
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_table_structure(database_name: str, table_name: str) -> dict:
    """Get table structure"""
    sys.stderr.write(
        f"[TRACE] get_table_structure trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    frappe.only_for("System Manager")

    # Security: table_name is interpolated into SQL below, so restrict it to a
    # plain identifier to prevent SQL injection.
    if not re.match(r"^[a-zA-Z0-9_]+$", table_name or ""):
        return {"success": False, "error": "Invalid table name"}

    try:
        if frappe.db.db_type == "postgres":
            # Query for postgres table structure
            query = f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table_name}'"
            cmd = ["psql", "-d", database_name, "-c", query, "--json=auto"]
            result = subprocess.run(cmd, capture_output=True, text=True)
        else:
            # Security: Use list to prevent command injection
            cmd = [
                "mysql",
                "-u",
                "root",
                "-e",
                f"DESCRIBE {table_name}",
                database_name,
                "--json",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            structure = json.loads(result.stdout)
            return {"success": True, "structure": structure}
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def export_database(database_name: str, export_format: str = "sql") -> dict:
    """Export database"""
    sys.stderr.write(
        f"[TRACE] export_database trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        export_file = f"/tmp/{database_name}_export.{export_format}"

        if frappe.db.db_type == "postgres":
            # pg_dump security: Use list and redirect stdout
            cmd = ["pg_dump", "-d", database_name, "-f", export_file]
            subprocess.run(cmd, check=True)
        else:
            if export_format == "sql":
                # Security: Use list and redirect stdout to file
                cmd = ["mysqldump", "-u", "root", database_name]
                with open(export_file, "w") as f:
                    subprocess.run(cmd, stdout=f, check=True)
            elif export_format == "csv":
                # Security: Use list and redirect stdout to file
                query = "SELECT * FROM table_name"
                cmd = ["mysql", "-u", "root", "-e", query, database_name]
                with open(export_file, "w") as f:
                    subprocess.run(cmd, stdout=f, check=True)

        return {"success": True, "file_path": export_file}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def import_database(database_name: str, import_file: str) -> dict:
    """Import database from SQL file"""
    sys.stderr.write(
        f"[TRACE] import_database trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    frappe.only_for("System Manager")

    # Security: only allow importing files from the site's private files dir so
    # an arbitrary caller-controlled path cannot be fed to psql/mysql.
    allowed_base = os.path.realpath(frappe.get_site_path("private", "files"))
    resolved_file = os.path.realpath(import_file)
    if resolved_file != allowed_base and not resolved_file.startswith(
        allowed_base + os.sep
    ):
        return {
            "success": False,
            "error": "Import file must be in the site's private files directory",
        }
    import_file = resolved_file

    try:
        if frappe.db.db_type == "postgres":
            # psql security: Use list and redirect stdin
            cmd = ["psql", "-d", database_name, "-f", import_file]
            subprocess.run(cmd, check=True)
        else:
            # Security: Use list and redirect stdin from file
            cmd = ["mysql", "-u", "root", database_name]
            with open(import_file, "r") as f:
                subprocess.run(cmd, stdin=f, check=True)

        return {"success": True, "message": "Database imported"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def optimize_database(database_name: str) -> dict:
    """Optimize all tables in database"""
    sys.stderr.write(
        f"[TRACE] optimize_database trace_id={getattr(getattr(__import__('frappe'), 'local', object()), 'trace_id', 'n/a')}\n"
    )
    try:
        if frappe.db.db_type == "postgres":
            cmd = ["psql", "-d", database_name, "-c", "VACUUM ANALYZE"]
            result = subprocess.run(cmd, capture_output=True, text=True)
        else:
            cmd = ["mysqlcheck", "-u", "root", "--optimize", database_name]
            result = subprocess.run(cmd, capture_output=True, text=True)

        return {"success": True, "output": result.stdout}
    except Exception as e:
        return {"success": False, "error": str(e)}
