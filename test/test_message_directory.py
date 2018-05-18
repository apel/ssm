"""
Created on 18 May 2018.

@author: Greg Corbett
"""

import shutil
import tempfile
import unittest

from ssm.message_directory import MessageDirectory


class TestMessageDirectory(unittest.TestCase):
    """Class used for testing the MessageDirectory class."""

    def setUp(self):
        """Create a MessageDirectory class on top of a temporary directory."""
        self.tmp_dir = tempfile.mkdtemp(prefix='message_directory')
        self.message_directory = MessageDirectory(self.tmp_dir)
        # Assert no files exist in the underlying file system.
        self.assertEqual(self.message_directory.count(), 0)

    def test_add_and_get(self):
        """
        Test the add and get methods of the MessageDirectory class.

        This test adds a file to a MessageDirectory, checks it has been
        written to the underlying directory and then checks the saved file
        for content equality.
        """
        test_content = "FOO"
        # Add the test content to the MessageDirectory.
        file_name = self.message_directory.add(test_content)

        # Assert there is exactly on message in the directory.
        self.assertEqual(self.message_directory.count(), 1)

        # Fetch the saved content using the get method.
        saved_content = self.message_directory.get(file_name)

        # Assert the saved content is equal to the original test content.
        self.assertEqual(saved_content, test_content)

    def test_count(self):
        """
        Test the count method of the MessageDirectory class.

        This test adds two files to a MessageDirectory and then checks
        the output of the count() function is as expected.
        """
        # Add some files to the MessageDirectory.
        self.message_directory.add("FOO")
        self.message_directory.add("BAR")

        # Check the count method returns the correct value.
        self.assertEqual(self.message_directory.count(), 2)

    def test_lock(self):
        """
        Test the lock method of the MessageDirectory class.

        This test checks the lock method returns true for any file.
        """
        self.assertTrue(self.message_directory.lock("any file"))

    def test_purge(self):
        """
        Test the purge method of the MessageDirectory class.

        This test only checks the purge method is callable without error,
        as the purge method only logs that it has been called.
        """
        self.message_directory.purge()

    def test_remove(self):
        """
        Test the remove method of the MessageDirectory class.

        This test adds a file, removes the file and then checks
        the number of files present.
        """
        # Add some files to the MessageDirectory.
        file_name = self.message_directory.add("FOO")
        # Use the remove method to delete the recently added file.
        self.message_directory.remove(file_name)
        # Check the count method returns the expected value.
        self.assertEqual(self.message_directory.count(), 0)

    def tearDown(self):
        """Remove test directory and all contents."""
        try:
            shutil.rmtree(self.tmp_dir)
        except OSError, error:
            print 'Error removing temporary directory %s' % self.tmp_dir
            print error


if __name__ == "__main__":
    unittest.main()
