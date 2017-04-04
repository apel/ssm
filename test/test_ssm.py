'''
Created on 7 Dec 2011

@author: will
'''

import ssm.ssm2
    
import os
import unittest
import shutil
import tempfile

from time import sleep
from OpenSSL import crypto


class TestSsm(unittest.TestCase):
    '''
    Class used for testing SSM.
    '''
    
    def setUp(self):
        '''
        Set up a test SSM, and a test directory, and a key/cert pair.
        '''
        if not (os.path.exists(TEST_CERT_FILE) and
                os.path.exists(TEST_KEY_FILE) and
                os.path.exists(EXPIRED_CERT_FILE)):

            # create a key pair
            key_pair = crypto.PKey()
            key_pair.generate_key(crypto.TYPE_RSA, 1024)
            open(TEST_KEY_FILE, "w").write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key_pair))

            # create a self-signed cert
            cert = crypto.X509()
            cert.get_subject().C = "UK"
            cert.get_subject().O = "STFC"
            cert.get_subject().OU = "SC"
            cert.get_subject().CN = "Test Cert"
            cert.set_serial_number(1000)
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(10*365*24*60*60)
            cert.set_issuer(cert.get_subject())
            cert.set_pubkey(key_pair)
            cert.sign(key_pair, 'sha1')

            open(TEST_CERT_FILE, "w").write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

            # create a short lived, self-signed, cert.
            # both certificates are signed by the same key
            expired_cert = crypto.X509()
            expired_cert.get_subject().C = "UK"
            expired_cert.get_subject().O = "STFC"
            expired_cert.get_subject().OU = "SC"
            expired_cert.get_subject().CN = "Test Cert"
            expired_cert.set_serial_number(1000)
            expired_cert.gmtime_adj_notBefore(0)
            expired_cert.gmtime_adj_notAfter(EXPIRED_CERT_LIFETIME)
            expired_cert.set_issuer(cert.get_subject())
            expired_cert.set_pubkey(key_pair)
            expired_cert.sign(key_pair, 'sha1')

            open(EXPIRED_CERT_FILE, "w").write(crypto.dump_certificate(crypto.FILETYPE_PEM, expired_cert))

        self._tmp_dir = tempfile.mkdtemp(prefix='ssm')
        
        self._valid_dn = '/test/dn'
        self.valid_dn_file, self.valid_dn_path = tempfile.mkstemp(prefix='valid', dir=self._tmp_dir)
        os.write(self.valid_dn_file, self._valid_dn)
        os.close(self.valid_dn_file)
        
        hosts_and_ports = [('not.a.broker', 123)]
        capath = '/not/a/path'
        check_crls = False
        pidfile = self._tmp_dir + '/pidfile'
        
        listen = '/topic/test'
        
        dest = '/topic/test'
        
        self._msgdir =  tempfile.mkdtemp(prefix='msgq')
        
        self._ssm = ssm.ssm2.Ssm2(hosts_and_ports, self._msgdir, TEST_CERT_FILE, TEST_KEY_FILE,
                                  dest=dest, listen=listen)


    def tearDown(self):
        '''Remove test directory and all contents.'''
        try:
            shutil.rmtree(self._msgdir)
            shutil.rmtree(self._tmp_dir)
            os.remove(TEST_CERT_FILE)
            os.remove(TEST_KEY_FILE)
            os.remove(EXPIRED_CERT_FILE)
        except OSError, e:
            print 'Error removing temporary directory %s' % self._tmp_dir
            print e
        
    def test_on_message(self):
        '''
        This is quite a complicated method, so it would take a long time
        to write a comprehensive test.  Instead, I will start with where there
        might be problems.
        '''
        # SSM crashed when headers were missing.  It should just ignore the
        # message.
        self._ssm.on_message({}, '')
        self._ssm.on_message({'nothing': 'dummy'}, '')
        self._ssm.on_message({'nothing': 'dummy'}, 'Not signed or encrypted.')

        # Try changing permissions on the directory we're writing to.
        # The on_message function shouldn't throw an exception.
        os.chmod(self._msgdir, 0400)
        self._ssm.on_message({'nothing': 'dummy'}, 'Not signed or encrypted.')
        os.chmod(self._msgdir, 0777)

    def test_init_expired_cert(self):
        """
        Test an exception is thrown when creating an
        SSM object with an expired certificate.
        """
        # Make sure expired certificate has expired       
        sleep(EXPIRED_CERT_LIFETIME * 2)

        try:
            self._ssm = ssm.ssm2.Ssm2(None, self._msgdir, EXPIRED_CERT_FILE, TEST_KEY_FILE,
                                      listen='/topic/test')

        except ssm.ssm2.Ssm2Exception, error:
            expected_error = ('Certificate %s has expired, '
                              'so cannot sign messages.' % EXPIRED_CERT_FILE)

            if str(error) == expected_error:
                # then this test has worked exactly as expected.
                return
            else:
                # otherwise this test may or may not have
                # failed, but something has gone wrong
                raise(error)

        # if the test gets here, then the test has
        # failed as no exception was thrown
        self.fail('A SSM was created with an expired certificate!')

TEST_CERT_FILE = '/tmp/test.crt'
EXPIRED_CERT_FILE = '/tmp/expired.crt'
EXPIRED_CERT_LIFETIME = 1

TEST_KEY_FILE = '/tmp/test.key'

if __name__ == '__main__':
    #import sys;sys.argv = ['', 'Test.test_get_a_broker']
    unittest.main()
