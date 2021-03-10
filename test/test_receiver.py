from __future__ import print_function

import os
import tempfile
from textwrap import dedent
import unittest

import mock

import bin.receiver
from ssm.ssm2 import Ssm2Exception


class getDNsTest(unittest.TestCase):
    def setUp(self):
        # Create a temporay file for use in the tests
        self.tf, self.tf_path = tempfile.mkstemp()
        os.close(self.tf)
        # Mock the logging to prevent errors due to it not being set up and so
        # that we can count how often logging methods are called
        self.patcher = mock.patch('bin.receiver.log')
        self.mock_log = self.patcher.start()

    def test_get_empty_dns_file(self):
        """Attempting to read an empty DNs file should raise an exception."""
        self.assertRaises(Ssm2Exception, bin.receiver.get_dns,
                          self.tf_path, self.mock_log)

    def test_get_good_dns(self):
        dn_text = dedent("""\
                         # Some kind of comment
                         /C=UK/O=eScience/OU=CLRC/L=RAL/CN=scarfrap.esc.rl.ac.uk
                         /C=UK/O=eScience/OU=CLRC/L=RAL/CN=uas-dev.esc.rl.ac.uk
                         # Another comment
                         /C=UK/ST=RAL/L=A City/O=eScene/OU=CC/CN=cld.grid.rl.uk
                         # A blank line

                         """)
        output = ['/C=UK/O=eScience/OU=CLRC/L=RAL/CN=scarfrap.esc.rl.ac.uk',
                  '/C=UK/O=eScience/OU=CLRC/L=RAL/CN=uas-dev.esc.rl.ac.uk',
                  '/C=UK/ST=RAL/L=A City/O=eScene/OU=CC/CN=cld.grid.rl.uk']
        f = open(self.tf_path, 'w')
        f.write(dn_text)
        f.close()
        self.assertEqual(bin.receiver.get_dns(self.tf_path, self.mock_log), output)

    def test_get_iffy_dns(self):
        """Check that the two bad DNs are picked up."""
        dn_text = dedent("""\
                         # A good DN
                         /C=UK/O=eScience/OU=CLRC/L=RAL/CN=scarfrap.esc.rl.ac.uk
                         # A bad DN
                         C=UK/ST=RAL/L=A City/O=eScene/OU=CC/CN=cld.grid.rl.uk
                         # Another bad DN
                         C=UK/O=eScene/OU=CLRC/L=RAL/CN=apel-dev.esc.rl.ac.uk
                         """)
        f = open(self.tf_path, 'w')
        f.write(dn_text)
        f.close()
        bin.receiver.get_dns(self.tf_path, self.mock_log)
        self.assertEqual(self.mock_log.warn.call_count, 2)

    def tearDown(self):
        os.remove(self.tf_path)
        self.patcher.stop()


if __name__ == '__main__':
    unittest.main()
