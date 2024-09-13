import os
import unittest
import tempfile
import shutil
import logging
from pathlib import Path
import time
from main import sync_folders, setup_logging

class TestFolderSync(unittest.TestCase):

    def setUp(self):
        # Create temporary directories for source and replica
        self.source_dir = tempfile.TemporaryDirectory()
        self.replica_dir = tempfile.TemporaryDirectory()

        # Create a temporary log file
        self.log_file = tempfile.NamedTemporaryFile(delete=False)
        self.log_file.close()  # We will let the logging system open and manage it

        # Set up logging for the tests
        setup_logging(self.log_file.name)
    
    def tearDown(self):
        # Shut down logging to release the log file
        logging.shutdown()

        # Remove the temporary log file
        os.remove(self.log_file.name)

        # Cleanup temporary directories
        self.source_dir.cleanup()
        self.replica_dir.cleanup()

    # Helper function to ensure proper file handling with retries
    def retry_operation(self, func, *args, retries=3, delay=0.1, **kwargs):
        for i in range(retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    raise e

    def test_file_copy(self):
        # Create a file in the source directory
        source_file_path = Path(self.source_dir.name) / "test_file.txt"
        self.retry_operation(self.create_file, source_file_path, "This is a test file.")

        # Run the sync process
        sync_folders(self.source_dir.name, self.replica_dir.name, dry_run=False, exclude_patterns=[])

        # Check if the file exists in the replica directory
        replica_file_path = Path(self.replica_dir.name) / "test_file.txt"
        self.assertTrue(replica_file_path.exists())
        self.assertEqual(self.read_file(replica_file_path), "This is a test file.")

    def test_file_deletion(self):
        # Create a file in the source and replica directories
        source_file_path = Path(self.source_dir.name) / "source_file.txt"
        replica_file_path = Path(self.replica_dir.name) / "replica_file.txt"

        self.retry_operation(self.create_file, source_file_path, "This is a source file.")
        self.retry_operation(self.create_file, replica_file_path, "This file should be deleted.")

        # Run the sync process
        sync_folders(self.source_dir.name, self.replica_dir.name, dry_run=False, exclude_patterns=[])

        # Check that the source file exists in the replica
        synced_file = Path(self.replica_dir.name) / "source_file.txt"
        self.assertTrue(synced_file.exists())

        # Check that the original replica-only file is deleted
        self.assertFalse(replica_file_path.exists())

    def test_exclude_patterns(self):
        # Create files in the source directory
        include_file = Path(self.source_dir.name) / "include_file.txt"
        exclude_file = Path(self.source_dir.name) / "exclude_file.tmp"

        self.retry_operation(self.create_file, include_file, "This file should be synced.")
        self.retry_operation(self.create_file, exclude_file, "This file should be excluded.")

        # Run the sync process with an exclusion pattern
        sync_folders(self.source_dir.name, self.replica_dir.name, dry_run=False, exclude_patterns=["*.tmp"])

        # Check that the included file exists in the replica
        replica_include_file = Path(self.replica_dir.name) / "include_file.txt"
        self.assertTrue(replica_include_file.exists())

        # Check that the excluded file does not exist in the replica
        replica_exclude_file = Path(self.replica_dir.name) / "exclude_file.tmp"
        self.assertFalse(replica_exclude_file.exists())

    def test_dry_run(self):
        # Create a file in the source directory
        source_file_path = Path(self.source_dir.name) / "test_file.txt"
        self.retry_operation(self.create_file, source_file_path, "This is a test file.")

        # Run the sync process with dry run enabled
        sync_folders(self.source_dir.name, self.replica_dir.name, dry_run=True, exclude_patterns=[])

        # Check that the file does NOT exist in the replica directory (due to dry run)
        replica_file_path = Path(self.replica_dir.name) / "test_file.txt"
        self.assertFalse(replica_file_path.exists())

    def test_error_handling(self):
        # Create a file in the replica directory and make it read-only to simulate an error
        replica_file_path = Path(self.replica_dir.name) / "readonly_file.txt"
        self.retry_operation(self.create_file, replica_file_path, "This file is read-only.")

        # Make the file read-only
        os.chmod(replica_file_path, 0o444)

        # Create a file in the source directory
        source_file_path = Path(self.source_dir.name) / "readonly_file.txt"
        self.retry_operation(self.create_file, source_file_path, "This file should overwrite the read-only file.")

        # Run the sync process and capture the logs
        sync_folders(self.source_dir.name, self.replica_dir.name, dry_run=False, exclude_patterns=[])

        # Check the log file for an error related to the read-only file
        with open(self.log_file.name, 'r') as log:
            log_content = log.read()
            self.assertIn("Failed to copy", log_content)

        # Restore write permissions to clean up (chmod to 0o666 allows writing)
        os.chmod(replica_file_path, 0o666)

    # Utility functions for file creation, reading, and operations with retries
    def create_file(self, file_path, content):
        with open(file_path, 'w') as f:
            f.write(content)

    def read_file(self, file_path):
        with open(file_path, 'r') as f:
            return f.read()

if __name__ == "__main__":
    unittest.main()
