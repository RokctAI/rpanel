
import unittest
from unittest.mock import patch, MagicMock
from rpanel.hosting.git_manager import clone_repository, pull_latest, switch_branch, rollback_deployment


class TestGitManager(unittest.TestCase):
    def setUp(self):
        self.website_name = "test-site"
        self.repo_url = "https://github.com/example/repo.git"

        # Mock website doc
        self.mock_website = MagicMock()
        self.mock_website.site_path = "/var/www/test-site"
        self.mock_website.git_branch = "main"

    @patch('rpanel.hosting.git_manager.frappe.db')
    @patch('rpanel.hosting.git_manager.frappe.get_doc')
    @patch('rpanel.hosting.git_manager.subprocess.run')
    @patch('rpanel.hosting.git_manager.os.path.exists')
    @patch('rpanel.hosting.git_manager.os.makedirs')
    @patch('rpanel.hosting.git_manager.os.listdir')
    def test_clone_repository_success(self, mock_listdir, mock_makedirs, mock_exists, mock_run, mock_get_doc, mock_db):
        # Setup
        mock_get_doc.return_value = self.mock_website
        mock_exists.return_value = False  # Directory doesn't exist
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        result = clone_repository(self.website_name, self.repo_url)

        # Verify
        self.assertTrue(result['success'])

        # Verify command
        args = mock_run.call_args[0][0]
        self.assertIn("git clone", " ".join(args) if isinstance(args, list) else args)

        # Verify DB commit was called
        mock_db.commit.assert_called()

        # Verify status update
        self.mock_website.db_set.assert_any_call('git_repository', self.repo_url)
        self.mock_website.db_set.assert_any_call('deployment_status', 'Success')

    @patch('rpanel.hosting.git_manager.frappe.db')
    @patch('rpanel.hosting.git_manager.frappe.get_doc')
    @patch('rpanel.hosting.git_manager.subprocess.run')
    @patch('rpanel.hosting.git_manager.os.path.exists')
    def test_clone_repository_not_empty(self, mock_exists, mock_run, mock_get_doc, mock_db):
        # Setup
        mock_get_doc.return_value = self.mock_website
        mock_exists.return_value = True  # Directory exists
        with patch('rpanel.hosting.git_manager.os.listdir', return_value=['file.txt']):
             result = clone_repository(self.website_name, self.repo_url)

        self.assertFalse(result['success'])
        self.assertIn("not empty", result['error'])

    @patch('rpanel.hosting.git_manager.frappe.db')
    @patch('rpanel.hosting.git_manager.frappe.get_doc')
    @patch('rpanel.hosting.git_manager.subprocess.run')
    @patch('rpanel.hosting.git_manager.os.path.exists')
    def test_pull_latest_success(self, mock_exists, mock_run, mock_get_doc, mock_db):
        # Setup
        mock_get_doc.return_value = self.mock_website
        mock_exists.return_value = True  # .git exists
        mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.")

        # Execute
        result = pull_latest(self.website_name)

        # Verify
        self.assertTrue(result['success'])
        mock_db.commit.assert_called()

    @patch('rpanel.hosting.git_manager.frappe.db')
    @patch('rpanel.hosting.git_manager.frappe.get_doc')
    @patch('rpanel.hosting.git_manager.subprocess.run')
    @patch('rpanel.hosting.git_manager.os.path.exists')
    def test_switch_branch_success(self, mock_exists, mock_run, mock_get_doc, mock_db):
        # Setup
        mock_get_doc.return_value = self.mock_website
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        result = switch_branch(self.website_name, "develop")

        # Verify
        self.assertTrue(result['success'])
        mock_db.commit.assert_called()
        self.mock_website.db_set.assert_any_call('git_branch', 'develop')

    @patch('rpanel.hosting.git_manager.frappe.db')
    @patch('rpanel.hosting.git_manager.frappe.get_doc')
    @patch('rpanel.hosting.git_manager.subprocess.run')
    @patch('rpanel.hosting.git_manager.os.path.exists')
    def test_rollback_success(self, mock_exists, mock_run, mock_get_doc, mock_db):
        # Setup
        mock_get_doc.return_value = self.mock_website
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        # Execute
        commit_hash = "abc1234"
        result = rollback_deployment(self.website_name, commit_hash)

        # Verify
        self.assertTrue(result['success'])
        mock_db.commit.assert_called()
