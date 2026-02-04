
import unittest
from unittest.mock import patch, MagicMock
import frappe
from rpanel.hosting.database_manager import export_database, import_database, optimize_database

class TestDatabaseManager(unittest.TestCase):

    @patch('rpanel.hosting.database_manager.subprocess.run')
    def test_export_database_sql(self, mock_run):
        """Test exporting database to SQL"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = export_database("test_db", "sql")
        
        self.assertTrue(result['success'])
        self.assertIn("test_db_export.sql", result['file_path'])
        
        # Verify mysqldump command
        args = mock_run.call_args[0][0]
        self.assertIn("mysqldump", args)
        self.assertIn("test_db", args)

    @patch('rpanel.hosting.database_manager.subprocess.run')
    def test_export_database_csv(self, mock_run):
        """Test exporting database to CSV"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = export_database("test_db", "csv")
        
        self.assertTrue(result['success'])
        self.assertIn("test_db_export.csv", result['file_path'])
        
        # Verify command
        args = mock_run.call_args[0][0]
        self.assertIn("SELECT * FROM table_name", args)

    @patch('rpanel.hosting.database_manager.subprocess.run')
    def test_import_database(self, mock_run):
        """Test importing database"""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = import_database("test_db", "/tmp/dump.sql")
        
        self.assertTrue(result['success'])
        
        # Verify command
        args = mock_run.call_args[0][0]
        self.assertIn("mysql -u root test_db < /tmp/dump.sql", args)

    @patch('rpanel.hosting.database_manager.subprocess.run')
    def test_optimize_database(self, mock_run):
        """Test optimizing database"""
        mock_run.return_value = MagicMock(returncode=0, stdout="Optimized")
        
        result = optimize_database("test_db")
        
        self.assertTrue(result['success'])
        
        # Verify command
        args = mock_run.call_args[0][0]
        cmd_str = " ".join(args) if isinstance(args, list) else args
        self.assertIn("mysqlcheck", cmd_str)
        self.assertIn("--optimize", cmd_str)
