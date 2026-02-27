
import unittest
from unittest.mock import patch, MagicMock, mock_open
import frappe
# Import the module to test. Note: This assumes rpanel is in python path
# or installed in bench
from rpanel.hosting.doctype.hosted_website.hosted_website import HostedWebsite


class TestHostedWebsite(unittest.TestCase):
    def setUp(self):
        # We simulate a document. In a real bench environment we might use frappe.get_doc,
        # but for unit testing controller logic, we can instantiate and mock.

        # HACK: Mock get_meta BEFORE instantiation to prevent DocType lookup
        # failures in unit tests
        self.patcher_meta = patch('frappe.get_meta')
        self.mock_meta = self.patcher_meta.start()

        # Configure the mock meta object
        meta_obj = MagicMock()
        meta_obj._table_doctypes = {} # Must be a dict to support .items()
        meta_obj.get_field = lambda x: MagicMock()
        self.mock_meta.return_value = meta_obj

        # Instantiate with dict to avoid DB lookup (init as new doc)
        self.doc = HostedWebsite({
            "doctype": "Hosted Website",
            "name": "test-website-doc"
        })
        self.doc.domain = "test.example.com"
        self.doc.client = "test-client"
        self.doc.system_user = "testuser"
        self.doc.status = "Active"
        self.doc.site_type = "CMS"
        self.doc.cms_type = "WordPress"
        self.doc.php_version = "8.3"
        self.doc.php_mode = "PHP-FPM"
        self.doc.site_path = "/var/www/testuser/data/www/test.example.com"
        self.doc.db_engine = "PostgreSQL"
        self.doc.db_name = "test_db"
        self.doc.db_user = "test_user"
        self.doc.db_password = "password"
        # Mock specific attributes that might be used
        self.doc.email_accounts = []
        self.doc.ssl_status = None

        # Mock DB methods to avoid hitting database for non-existent doc
        self.doc.save = MagicMock()
        self.doc.db_set = MagicMock()
        self.doc.db_update = MagicMock()
        self.doc.check_client_quota = MagicMock()
        self.doc.load_from_db = MagicMock()
        self.doc.reload = MagicMock()

    def tearDown(self):
        self.patcher_meta.stop()

    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.SystemUserManager')
    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.PHPFPMManager')
    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.subprocess.run')
    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.os.path.exists')
    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.run_mysql_command')
    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.create_pg_database')
    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.run_certbot')
    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.update_exim_config')
    @patch('builtins.open', new_callable=mock_open)
    def test_provision_site_success(
            self,
            mock_file,
            mock_exim,
            mock_certbot,
            mock_pg,
            mock_mysql,
            mock_exists,
            mock_run,
            MockPHP,
            MockUser):
        """Test successful site provisioning for a CMS"""
        # Setup mocks
        mock_exists.return_value = False  # Directory doesn't exist yet
        mock_run.return_value.returncode = 0  # Success for check=True
        mock_certbot.return_value = (True, "Cert issued")
        mock_exim.return_value = (True, "Exim updated")

        mock_user_instance = MockUser.return_value
        mock_user_instance.user_exists.return_value = False

        mock_php_instance = MockPHP.return_value
        mock_php_instance.create_pool.return_value = "/run/php/test.sock"

        # Mock NginxManager inside HostedWebsite?
        # The code does `self.update_nginx_config()` which writes files.
        # HostedWebsite.update_nginx_config writes to /etc/nginx... we need to mock open/subprocess there too within the method
        # But we mocked subprocess.run globally for the module, so that should
        # cover it.

        # Execute
        # We need to mock install_wordpress separately to avoid those specific
        # calls if they are complex
        with patch.object(self.doc, 'install_wordpress') as mock_install:
            self.doc.provision_site()

            # Verify interactions

            # 1. System User
            mock_user_instance.create_user.assert_called_with("testuser")

            # 2. PHP-FPM
            mock_php_instance.create_pool.assert_called()
            self.assertEqual(self.doc.php_fpm_socket, "/run/php/test.sock")

            # 3. Directory Creation
            # subprocess.run should be called for mkdir, chown, chmod
            self.assertTrue(mock_run.called)

            # 4. Database Setup
            if self.doc.db_engine == "MariaDB":
                mock_mysql.assert_called()
            else:
                mock_pg.assert_called_with("test_db", "test_user", "password")

            # 5. WP Install
            mock_install.assert_called()

    def test_validate_domain(self):
        """Test domain validation regex"""
        self.doc.domain = "Invalid Domain"
        with self.assertRaises(frappe.exceptions.ValidationError):
            self.doc.validate()

        self.doc.domain = "valid-domain.com"
        # Since we are testing validate(), we might need to mock
        # check_client_quota too if it hits DB
        with patch.object(self.doc, 'check_client_quota') as mock_quota:  # noqa: F841
            self.doc.validate()
            # Should pass without error

    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.SystemUserManager')
    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.PHPFPMManager')
    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.subprocess.run')
    @patch('rpanel.hosting.doctype.hosted_website.hosted_website.os.path.exists')
    def test_deprovision_site(self, mock_exists, mock_run, MockPHP, MockUser):
        """Test site deprovisioning"""
        mock_exists.return_value = True  # Configs exist
        self.doc.php_fpm_socket = "/run/php/test.sock"

        mock_user_instance = MockUser.return_value
        mock_user_instance.get_user_reference_count.return_value = 0  # No other sites

        self.doc.deprovision_site()

        # Verify interactions
        MockPHP.return_value.delete_pool.assert_called_with("test.example.com")
        mock_user_instance.delete_user.assert_called_with("testuser")

        # Verify Nginx config removal (subprocess calls)
        # Should call rm for config
        called_rm_nginx = False
        for call in mock_run.call_args_list:
            args = call[0][0]  # Access positional args
            if 'rm' in args and '/etc/nginx/conf.d/test.example.com.conf' in args:
                called_rm_nginx = True

        self.assertTrue(
            called_rm_nginx,
            "Should attempt to remove Nginx config")
