# Copyright 2018 Science and Technology Facilities Council
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This module contains test cases for the MessageDirectory class."""
from __future__ import print_function

import shutil
import tempfile
import time
import unittest

from ssm.message_directory import MessageDirectory


class TestMessageDirectory(unittest.TestCase):
    """Class used for testing the MessageDirectory class."""

    def setUp(self):
        """Create a MessageDirectory class on top of a temporary directory."""
        self.tmp_dir = tempfile.mkdtemp(prefix='message_directory')
        self.message_directory = MessageDirectory(self.tmp_dir)

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

    def test_orderd_file_retrieval(self):
        """
        Test the messages are retrieved in the order they were last modified.

        This test adds files to the MessageDirectory and then iterates over
        the MessageDirectory to retrieve the file names. If the for loop does
        not return them in the order they were last modfied, this test fails.
        """
        # In the event of a failure of underlying _get_messages sorting, it's
        # possible the returned list of files could still be in the correct
        # order by random chance.
        # A 'large' list of test_content reduces this chance.
        test_content_list = ["Lobster Thermidor", "Crevettes", "Mornay sauce",
                             "Truffle Pate", "Brandy", "Fried egg", "Spam"]

        # A list to hold file names by creation time.
        file_names_by_creation_time = []
        for test_content in test_content_list:
            # Add the content to the MessageDirectory.
            file_name = self.message_directory.add(test_content)
            # Append the file name to the list of file names by create time.
            file_names_by_creation_time.append(file_name)
            # Wait a small amount of time to allow differentiation of times.
            time.sleep(0.02)

        self.assertEqual(self.message_directory.count(), 7)

        # A list to hold file names by modification time.
        file_names_by_modification_time = []
        # Use a for loop (similar to how the SSM retrieves messages)
        # to build up an ordered list of files.
        for file_name in self.message_directory:
            file_names_by_modification_time.append(file_name)

        # As the files are not modified once added to the MessageDirectory,
        # the two lists of file names should be equal.
        self.assertEqual(file_names_by_modification_time,
                         file_names_by_creation_time)

    def test_count(self):
        """
        Test the count method of the MessageDirectory class.

        This test adds two files to a MessageDirectory and then checks
        the output of the count() function is as expected.
        """
        self.assertEqual(self.message_directory.count(), 0)
        self.message_directory.add("FOO")
        self.assertEqual(self.message_directory.count(), 1)
        self.message_directory.add("BAR")
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
        # Check the directory starts empty
        self.assertEqual(self.message_directory.count(), 0)
        # Add some files to the MessageDirectory.
        file_name = self.message_directory.add("FOO")
        self.assertEqual(self.message_directory.count(), 1)
        # Use the remove method to delete the recently added file.
        self.message_directory.remove(file_name)
        # Check the count method returns the expected value.
        self.assertEqual(self.message_directory.count(), 0)

    def test_dir_in_dir(self):
        """Check that directories inside the queue are being ignored."""
        self.longMessage = True  # Include normal unittest output before custom message.

        with tempfile.TemporaryFile(dir=self.tmp_dir):
            tempfile.mkdtemp(prefix='extra_directory_', dir=self.tmp_dir)
            self.assertEqual(self.message_directory.count(), 1, "Expected just one file, "
                             "but greater result implies that directory is being counted.")

    def tearDown(self):
        """Remove test directory and all contents."""
        try:
            shutil.rmtree(self.tmp_dir)
        except OSError as error:
            print('Error removing temporary directory %s' % self.tmp_dir)
            print(error)


if __name__ == "__main__":
    unittest.main()
