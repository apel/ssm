import os
import tempfile
import unittest

import bin.receiver
from ssm.ssm2 import Ssm2Exception


class getDNsTest(unittest.TestCase):
    def setUp(self):
        self.tf, self.tf_path = tempfile.mkstemp()
        os.close(self.tf)

    def test_empty_dns_file(self):
        self.assertRaises(Ssm2Exception, bin.receiver.get_dns, self.tf_path)

    def tearDown(self):
        os.remove(self.tf_path)


if __name__ == '__main__':
    unittest.main()
