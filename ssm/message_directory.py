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

class MessageDirectory(object):
    """A structure for holding Accounting messages in a directory."""

    def __init__(self, path):
        """Create a new directory structure for holding Accounting messages."""
        raise NotImplementedError()

    def add(self, data):
        """Add a new element to the queue and return its name."""
        raise NotImplementedError()

    def count(self):
        """
        Return the number of elements in the queue.

        Regardless of their state.
        """
        raise NotImplementedError()

    def get(self, name):
        """Get an element data from a locked element."""
        raise NotImplementedError()

    def lock(self, name):
        """Lock an element."""
        raise NotImplementedError()

    def purge(self):
        """
        Purge the queue.

        - delete unused intermediate directories
        - delete too old temporary directories
        - unlock too old locked directories

        """
        raise NotImplementedError()

    def remove(self, name):
        """Remove locked element from the queue."""
        raise NotImplementedError()
