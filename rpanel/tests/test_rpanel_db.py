import unittest
import frappe
from unittest.mock import patch, MagicMock
from rpanel.hosting.database_manager import (
    export_database,
    import_database,
    optimize_database,
)


class TestDatabaseManager(unittest.TestCase):
    @patch("rpanel.hosting.database_manager.frappe.db")
    @patch("rpanel.hosting.database_manager.subprocess.run")
    def test_export_database_sql(self, mock_run, mock_db):
        """Test exporting database to SQL"""
        mock_db.db_type = "postgres"
        mock_run.return_value = MagicMock(returncode=0)

        result = export_database("test_db", "sql")

        self.assertTrue(result["success"])
        self.assertIn("test_db_export.sql", result["file_path"])

        # Verify command based on DB type
        args = mock_run.call_args[0][0]
        self.assertIn("pg_dump", args)
        self.assertIn("test_db", args)

    @patch("rpanel.hosting.database_manager.frappe.db")
    @patch("rpanel.hosting.database_manager.subprocess.run")
    def test_export_database_csv(self, mock_run, mock_db):
        """Test exporting database to CSV"""
        mock_db.db_type = "postgres"
        mock_run.return_value = MagicMock(returncode=0)

        result = export_database("test_db", "csv")

        self.assertTrue(result["success"])
        self.assertIn("test_db_export.csv", result["file_path"])

        # Verify command
        args = mock_run.call_args[0][0]
        self.assertIn("pg_dump", args)

    @patch("rpanel.hosting.database_manager.frappe.db")
    @patch("rpanel.hosting.database_manager.subprocess.run")
    def test_import_database(self, mock_run, mock_db):
        """Test importing database"""
        mock_db.db_type = "postgres"
        mock_run.return_value = MagicMock(returncode=0)

        result = import_database("test_db", "/tmp/dump.sql")

        self.assertTrue(result["success"])

        # Verify command
        args = mock_run.call_args[0][0]
        self.assertIn("psql", args)
        self.assertIn("test_db", args)

    @patch("rpanel.hosting.database_manager.frappe.db")
    @patch("rpanel.hosting.database_manager.subprocess.run")
    def test_optimize_database(self, mock_run, mock_db):
        """Test optimizing database"""
        mock_db.db_type = "postgres"
        mock_run.return_value = MagicMock(returncode=0, stdout="Optimized")

        result = optimize_database("test_db")

        self.assertTrue(result["success"])

        # Verify command
        args = mock_run.call_args[0][0]
        cmd_str = " ".join(args) if isinstance(args, list) else args
        self.assertIn("psql", cmd_str)
        self.assertIn("VACUUM", cmd_str)
