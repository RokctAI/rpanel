
import unittest
from unittest.mock import patch, MagicMock, mock_open
from rpanel.hosting.nginx_manager import NginxManager
from rpanel.hosting.database_manager import execute_query, get_tables
from rpanel.hosting.system_user_manager import SystemUserManager
from rpanel.hosting.email_manager import generate_dkim_keys, get_spf_record


class TestNginxManager(unittest.TestCase):
    def setUp(self):
        self.manager = NginxManager()
        self.domain = "test.example.com"
        self.site_path = "/var/www/test.example.com"

    @patch('rpanel.hosting.nginx_manager.subprocess.run')
    @patch('rpanel.hosting.nginx_manager.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_create_website_config(self, mock_file, mock_exists, mock_run):
        """Test creating a new website configuration"""
        mock_exists.return_value = False  # Config doesn't exist yet
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        self.manager.create_website_config(self.domain, self.site_path)

        # Verify subprocess calls (tee, chmod, ln, nginx -t, reload)
        self.assertTrue(mock_run.called)

        # Verify checking for protected configs
        self.assertFalse(self.manager.is_protected_config("rpanel-test_example_com.conf"))

    def test_is_protected_config(self):
        """Test protected configuration detection"""
        self.assertTrue(self.manager.is_protected_config("frappe-bench-frappe"))
        self.assertFalse(self.manager.is_protected_config("rpanel-random-site.conf"))

    @patch('rpanel.hosting.nginx_manager.subprocess.run')
    def test_enable_disable_site(self, mock_run):
        """Test enabling and disabling sites"""
        mock_run.return_value = MagicMock(returncode=0)
        config_name = "rpanel-test_site.conf"

        # Enable
        with patch('rpanel.hosting.nginx_manager.Path.exists') as mock_exists:
            mock_exists.return_value = False  # Target symlink doesn't exist
            self.manager.enable_site(config_name)
            mock_run.assert_called()  # Should call ln -s

        # Disable
        self.manager.disable_site(config_name)
        mock_run.assert_called()  # Should call rm -f

    @patch('rpanel.hosting.nginx_manager.subprocess.run')
    def test_test_and_reload_success(self, mock_run):
        """Test successful Nginx reload"""
        # Mock nginx -t success
        mock_run.return_value = MagicMock(returncode=0, stdout="syntax is ok", stderr="")

        self.manager.test_and_reload()

        # Should call systemctl reload nginx
        found_reload = False
        for call in mock_run.call_args_list:
            args = call[0][0]
            if args == ['sudo', 'systemctl', 'reload', 'nginx']:
                found_reload = True
                break
        self.assertTrue(found_reload)


class TestDatabaseManager(unittest.TestCase):
    @patch('rpanel.hosting.database_manager.subprocess.run')
    def test_execute_query_select(self, mock_run):
        """Test executing valid SELECT query"""
        mock_run.return_value = MagicMock(returncode=0, stdout='[{"id": 1, "name": "Test"}]')

        result = execute_query("test_db", "SELECT * FROM users")

        self.assertTrue(result['success'])
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(result['data'][0]['name'], "Test")

    def test_execute_query_blocked(self):
        """Test blocking non-SELECT queries"""
        result = execute_query("test_db", "DROP TABLE users")
        self.assertFalse(result['success'])
        self.assertIn("Only SELECT", result['error'])

    @patch('rpanel.hosting.database_manager.subprocess.run')
    def test_get_tables(self, mock_run):
        """Test retrieving tables"""
        mock_run.return_value = MagicMock(returncode=0, stdout='["table1", "table2"]')

        result = get_tables("test_db")

        self.assertTrue(result['success'])
        self.assertEqual(result['tables'], ["table1", "table2"])


class TestSystemUserManager(unittest.TestCase):
    def setUp(self):
        self.manager = SystemUserManager()
        self.username = "testuser"

    @patch('rpanel.hosting.system_user_manager.subprocess.run')
    def test_user_exists(self, mock_run):
        """Test user existence check"""
        mock_run.return_value = MagicMock(returncode=0)  # User exists
        self.assertTrue(self.manager.user_exists(self.username))

        mock_run.return_value = MagicMock(returncode=1)  # User does not exist
        self.assertFalse(self.manager.user_exists(self.username))

    @patch('rpanel.hosting.system_user_manager.subprocess.run')
    @patch('rpanel.hosting.system_user_manager.SystemUserManager.user_exists')
    def test_create_user(self, mock_exists, mock_run):
        """Test user creation with limited privileges"""
        mock_exists.return_value = False

        self.manager.create_user(self.username)

        # Verify useradd args
        found_useradd = False
        for call in mock_run.call_args_list:
            args = call[0][0]
            if 'useradd' in args and '/bin/false' in args:
                found_useradd = True
                break
        self.assertTrue(found_useradd, "Should create user with no shell")

    @patch('rpanel.hosting.system_user_manager.subprocess.run')
    @patch('rpanel.hosting.system_user_manager.SystemUserManager.user_exists')
    def test_delete_user(self, mock_exists, mock_run):
        """Test user deletion"""
        mock_exists.return_value = True

        self.manager.delete_user(self.username)

        # Verify userdel called
        found_del = False
        for call in mock_run.call_args_list:
            args = call[0][0]
            if 'userdel' in args and self.username in args:
                found_del = True
                break
        self.assertTrue(found_del)


class TestEmailManager(unittest.TestCase):
    @patch('rpanel.hosting.email_manager.subprocess.run')
    @patch('rpanel.hosting.email_manager.os.path.exists')
    @patch('rpanel.hosting.email_manager.os.makedirs')
    @patch('rpanel.hosting.email_manager.os.rename')
    @patch('builtins.open', new_callable=mock_open, read_data='p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ')
    def test_generate_dkim_keys(self, mock_file, mock_rename, mock_makedirs, mock_exists, mock_run):
        """Test DKIM key generation"""
        mock_exists.return_value = False

        result = generate_dkim_keys("test.com")

        self.assertTrue(result['success'])
        mock_run.assert_called()  # Verify opendkim-genkey called
        self.assertEqual(result['public_key'], "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ")

    def test_get_spf_record(self):
        """Test SPF record generation"""
        # Test with provided IP
        record = get_spf_record("test.com", "1.2.3.4")
        self.assertIn("ip4:1.2.3.4", record['value'])

        # Test with default (mocking socket would be needed to be precise, but structure check is enough)
        with patch('socket.gethostbyname') as mock_ip:
            mock_ip.return_value = "127.0.0.1"
            record = get_spf_record("test.com")
            self.assertIn("ip4:127.0.0.1", record['value'])
