"""Unit tests for bin/sender.py."""
import sys
import unittest

import bin.sender


class mainTest(unittest.TestCase):
    """Test cases for sender.main."""

    def setUp(self):
        # Clear arguments to avoid args from coverage.py being passed in.
        sys.argv = []

    def test_main_no_config(self):
        """Check that a sender can't be started without a config."""
        self.assertRaises(SystemExit, bin.sender.main)


if __name__ == '__main__':
    unittest.main()
