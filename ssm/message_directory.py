"""
Copyright (C) 2018 STFC.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

@author: Greg Corbett
"""

import logging
import os
import uuid

# logging configuration
LOG = logging.getLogger(__name__)


class MessageDirectory(object):
    """A structure for holding Accounting messages in a directory."""

    def __init__(self, path):
        """Create a new directory structure for holding Accounting messages."""
        self.directory_path = path

    def add(self, data):
        """Add the passed data to a new file and return it's name."""
        # Create a unique file name so APEL admins can pair sent and recieved
        # messages easily (as the file name appears in the sender and receiver
        # logs as the message ID).
        name = uuid.uuid4()

        try:
            # Open the file and write the provided data into the file.
            with open("%s/%s" % (self.directory_path, name), 'w') as message:
                message.write(data)
        except (IOError, OSError) as error:
            LOG.error("Could not create file %s/%s: %s",
                      self.directory_path, name, error)

        # Return the name of the created file as a string,
        # to keep the dirq like interface.
        return "%s" % name

    def count(self):
        """
        Return the number of elements in the queue.

        Regardless of their state.
        """
        return len(self._get_messages())

    def get(self, name):
        """Return the content of the named message."""
        with open("%s/%s" % (self.directory_path, name)) as message:
            content = message.read()
        return content

    def lock(self, _name):
        """Return True to simulate a successful lock. Does nothing else."""
        return True

    def purge(self):
        """
        Do nothing, as there are no old/intermediate directories to purge.

        Only included to preserve dirq interface.
        """
        LOG.debug("purge() called, but purge() does nothing.")

    def remove(self, name):
        """Remove the named message."""
        try:
            os.unlink("%s/%s" % (self.directory_path, name))
        except (IOError, OSError) as error:
            LOG.warning("Could not remove %s, it may get resent.", name)
            LOG.debug(error)

    def _get_messages(self, sort_by_mtime=False):
        """
        Get the messages stored in this MessageDirectory.

        if sort_by_mtime is set to True, the returned list is guaranteed to be
        in increasing order of modification time.

        mtime is used because (apparently) there is not way to find the
        original date of file creation due to a limitation
        of the underlying filesystem
        """
        try:
            # Get a list of files under self.directory_path
            # in an arbitrary order.
            file_name_list = os.listdir(self.directory_path)

            if sort_by_mtime:
                # Working space to hold the unsorted messages
                # as file paths and mtimes.
                unsorted_messages = []
                # Working space to hold the sorted messages as file names.
                sorted_messages = []

                # Work out the mtime of each file.
                for file_name in file_name_list:
                    file_path = os.path.join(self.directory_path, file_name)
                    # Store the file path and the time
                    # the file was last modified.
                    unsorted_messages.append((file_name,
                                              os.path.getmtime(file_path)))

                # Sort the file paths by mtime and
                # then only store the file name.
                for (file_name, _mtime) in sorted(unsorted_messages,
                                                  key=lambda tup: tup[1]):
                    # Store the sorted file paths in a class element.
                    sorted_messages.append(file_name)

                # Return the sorted list.
                return sorted_messages

            # If we get here, just return the arbitrarily ordered list.
            return file_name_list

        except (IOError, OSError) as error:
            LOG.error(error)
            # Return an empty file list.
            return []


    def __iter__(self):
        """Return an iterable of the files currently in the MessageDirectory."""
        return self._get_messages(sort_by_mtime=True).__iter__()
