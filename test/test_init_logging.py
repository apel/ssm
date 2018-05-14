"""Unit tests for ssm/__init__.py."""

import unittest

import ssm


class setUpLoggingTest(unittest.TestCase):
    """Test cases for the set_up_logging function in ssm.__init__."""

    def test_none_argurments(self):
        """Check that calling the function with all None args fails."""
        self.assertRaises(KeyError, ssm.set_up_logging, None, None, None)


if __name__ == '__main__':
    unittest.main()
