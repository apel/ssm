'''
Created on 7 Dec 2011

@author: will
'''

import ssm.ssm2
    
import os
import unittest
import shutil
import tempfile

from subprocess import call


class TestSsm(unittest.TestCase):
    '''
    Class used for testing SSM.
    '''
    
    def setUp(self):
        '''
        Set up a test SSM, and a test directory, and new valid cert.
        '''

        # Some of the functions require the hardcoded
        # expired certificate and key to be files.
        _, self._key_path = tempfile.mkstemp(prefix='key')
        with open(self._key_path, 'w') as key_path:
            key_path.write(TEST_KEY)

        _, self._expired_cert_path = tempfile.mkstemp(prefix='cert')
        with open(self._expired_cert_path, 'w') as expired_cert_path:
            expired_cert_path.write(EXPIRED_CERT)

        # Create a new cert using the hardcoded key
        # The subj has been hardcoded so the generated certificate
        # subject matches the subject of the hardcoded, expired,
        # certificate at the bottom of this file
        call(['openssl', 'req', '-x509', '-nodes', '-days', '1',
              '-new', '-key', self._key_path,
              '-out', TEST_CERT_FILE, '-subj',
              '/C=UK/O=STFC/OU=SC/CN=Test Cert'])

        self._tmp_dir = tempfile.mkdtemp(prefix='ssm')

        # Store these variables as class variables so new SSMs can be
        # instantiated in each test method. (We cant simply create the
        # as SSM here as one of the two tests checks the instantiation
        # fails as it is expected to with a expired certificate.)
        self._valid_dn = '/test/dn'
        self.valid_dn_file, self.valid_dn_path = tempfile.mkstemp(prefix='valid', dir=self._tmp_dir)
        os.write(self.valid_dn_file, self._valid_dn)
        os.close(self.valid_dn_file)
        
        self._hosts_and_ports = [('not.a.broker', 123)]
        self._capath = '/not/a/path'
        self._check_crls = False
        self._pidfile = self._tmp_dir + '/pidfile'
        
        self._listen = '/topic/test'
        
        self._dest = '/topic/test'
        
        self._msgdir =  tempfile.mkdtemp(prefix='msgq')
        
    def tearDown(self):
        '''Remove test directories and files.'''
        try:
            shutil.rmtree(self._msgdir)
            shutil.rmtree(self._tmp_dir)
            os.remove(TEST_CERT_FILE)
            os.remove(self._key_path)
            os.remove(self._expired_cert_path)
        except OSError, e:
            print 'Error removing temporary directory/file'
            print e
        
    def test_on_message(self):
        '''
        This is quite a complicated method, so it would take a long time
        to write a comprehensive test.  Instead, I will start with where there
        might be problems.
        '''
        test_ssm = ssm.ssm2.Ssm2(self._hosts_and_ports, self._msgdir,
                                 TEST_CERT_FILE, self._key_path,
                                 dest=self._dest, listen=self._listen)
        # SSM crashed when headers were missing.  It should just ignore the
        # message.
        test_ssm.on_message({}, '')
        test_ssm.on_message({'nothing': 'dummy'}, '')
        test_ssm.on_message({'nothing': 'dummy'}, 'Not signed or encrypted.')

        # Try changing permissions on the directory we're writing to.
        # The on_message function shouldn't throw an exception.
        os.chmod(self._msgdir, 0400)
        test_ssm.on_message({'nothing': 'dummy'}, 'Not signed or encrypted.')
        os.chmod(self._msgdir, 0777)

    def test_init_expired_cert(self):
        """Test exception is thrown creating an SSM with an expired cert."""
        try:
            # Indirectly test crypto.verify_cert_date
            test_ssm = ssm.ssm2.Ssm2(self._hosts_and_ports, self._msgdir,
                                     self._expired_cert_path, self._key_path,
                                     listen=self._listen)

        except ssm.ssm2.Ssm2Exception, error:
            expected_error = ('Certificate %s has expired, '
                              'so cannot sign messages.'
                              % self._expired_cert_path)

            if str(error) == expected_error:
                # then this test has worked exactly as expected.
                return
            else:
                # otherwise this test may or may not have
                # failed, but something has gone wrong
                raise error

        # if the test gets here, then the test has
        # failed as no exception was thrown
        self.fail('A SSM was created with an expired certificate!')

TEST_CERT_FILE = '/tmp/test.crt'

# As we want the expired cert to match the key used,
# we can't generate them on the fly.
# The cert below has the subject
# '/C=UK/O=STFC/OU=SC/CN=Test Cert'
EXPIRED_CERT = '''-----BEGIN CERTIFICATE-----
MIIDTTCCAjWgAwIBAgIJAI/H+MkYrMbMMA0GCSqGSIb3DQEBBQUAMD0xCzAJBgNV
BAYTAlVLMQ0wCwYDVQQKDARTVEZDMQswCQYDVQQLDAJTQzESMBAGA1UEAwwJVGVz
dCBDZXJ0MB4XDTE3MDQxODE1MDM1M1oXDTE3MDQxOTE1MDM1M1owPTELMAkGA1UE
BhMCVUsxDTALBgNVBAoMBFNURkMxCzAJBgNVBAsMAlNDMRIwEAYDVQQDDAlUZXN0
IENlcnQwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC3n//lZBP0LIUI
9vnNAMPgDHeY3wTqDSUWPKbrmr5VqTdMjWSLF32WM3dgpagBywqSKYyo64jwnkon
KDlp5F1ji1Mw98cagSmZo9ZnBNqjZYGD/3n1MPgGh6RAZEmXDtHbjO93Afk+JS6p
z+JGKveDA/+FfKVe9li4B7kYnfzqd+hR7CNPq9i6kJTwqKhv7PLPWUq/xF5w6ymx
TYqhxjgEgT6KBpRMNk9uG97LrSFiDRhurc13r2FZeAtJygK1OhGrq/f9Ptvf3Q0f
dbnJ/7kEOtVXfeTIeellI5DNMo+O8oSHMeCHPQBFGvLZIK9gPhj/XpNtGOkZK1Rk
SdqNfNzdAgMBAAGjUDBOMB0GA1UdDgQWBBQXikGk4aUeus+fd0EWxDdY+5VX5DAf
BgNVHSMEGDAWgBQXikGk4aUeus+fd0EWxDdY+5VX5DAMBgNVHRMEBTADAQH/MA0G
CSqGSIb3DQEBBQUAA4IBAQAStgDqGi/GtRZUfXojFu2vOyfvOqY24uHQLODtIRN+
nQqppV6LzA4ZbgxvrM0usVwFuVG5QD3ZP2dZ7pwS7FCu7JG9NQctgkM4bR9SM/St
1QPOhNsU8GQT0iD8VPFe4Y/I04Kn88+fNBiwe7txPC3aUUvMG5rEukDHlabw2tVi
l0+9Nckw4KIywSgA4DOccRdalm/xSDM3rVI87EpD4NQdXAl+18Z0bXDYGavaV1FG
uMvzfkzYoyCtL0CxuZEYbxXHUMrJ0fAdHC/itYVwtssNmtlw9yG+S87yVr89mEI5
BwQaxGNoKpW2K5w4e6KK0d1SAvDnIcTUONt3nQZND9sH
-----END CERTIFICATE-----'''

# A key used to generate the above, expired, certificate and the
# certificates generated by the test methods
TEST_KEY = '''-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC3n//lZBP0LIUI
9vnNAMPgDHeY3wTqDSUWPKbrmr5VqTdMjWSLF32WM3dgpagBywqSKYyo64jwnkon
KDlp5F1ji1Mw98cagSmZo9ZnBNqjZYGD/3n1MPgGh6RAZEmXDtHbjO93Afk+JS6p
z+JGKveDA/+FfKVe9li4B7kYnfzqd+hR7CNPq9i6kJTwqKhv7PLPWUq/xF5w6ymx
TYqhxjgEgT6KBpRMNk9uG97LrSFiDRhurc13r2FZeAtJygK1OhGrq/f9Ptvf3Q0f
dbnJ/7kEOtVXfeTIeellI5DNMo+O8oSHMeCHPQBFGvLZIK9gPhj/XpNtGOkZK1Rk
SdqNfNzdAgMBAAECggEBAKZaAQ3juGAA5RTWCkA6bTlQkhigEmenOO4ITIAtVDlu
b3aesXOA+HlWbtPTv3zAYPdBRPjTSOATxsHqovjXtfM0iU1Xa70LPpC96MKzlw9o
KglXLTl//3KK97aOJE0BVAU+jMKXuyEdtkSI3EkNK+Y5fQeFgJujOYSfGoS+vB38
sCXKR1CcD5L1NO3iql/vNKyMpw+xVR85VAOVhAaF5d/VEkfO6onAa47oHKmXWs5A
rs7WmkKZqrpiAXtxPjgIKg8JLG5nDOcWBqSccMwpdVvVGWjjyh09qQ2Q1gvvcrNr
dv0GqFhWsm+rwb8Ih3aaPxxvPu8TDhsb908gfdylOFECgYEA8PssPKdTdZlFoYKm
oArMriJdXxKHr5a6XrnqDJDgzVVgx7BmCQg+I+nGhZd1hK+ZX1rcuMagE2rFrMM+
16EoRgTJ0ETxBwbqMIp4wzSoOO0ybK2fzj/CzeMfcI6lj7aIfRPscHbmDuaXwEbR
nbKxiBTcQ4zXjT11FL46tJFwba8CgYEAwxG3RcxBsGs+zzKBw6vH7PC5rQQk2AlD
zXIumNVeKZ7H8U0kxKB0DQbcjQ8VftXUBtRtXr7xr244I5XvAUzaroZbyNy7eYyD
hgqeLxC37D3UE1VIO0Qfybmc5zjIpWOFSVmDm6Jx1iSWRE6NVn95d09GMOhERLzZ
BplQefk07TMCgYAj0WGA3moER7TWzcGQdip4E3mHYQyz55Zp7/4+weX3/yG0bJ6t
5wC9e8jbIGkCQMtuJeY6vKMcX7lj9V1I1ZZT2fBZOXYN0lRKxLowYYpDc9YT2zau
hEGjMogAxeML2litJqH1EWcefd2+YYhUhTPoAxm+HJgJUUIuxBubrSZl1wKBgFr1
RM8wCiVYLKZyt51k2Ul7iijJ+OAfmdUPe/jZ7RldJ4A154IkC1kTrP29XdmRnVc9
8G2wfYO+0kCNpi+mBYZBskS74FMyGRYEl3P8yLZIsj39kzvHbUcj3KzYhn7QJBNq
wPpuScR/tO3O7wq5UAs5FNKzSzn+EPiJvsPRV0OPAoGAA7DCsWuwGJcv867ox5ll
rXWxb6CWrJPVDwlSJi4TIQuuuoPaAll5MwMvIZAwWqtMpqgSDzqYewMPTVwP/MYF
IxueZv7Dhxzr4GoJ9EfLfN9IHj5EP8YQ6dKyY8P1YN8siV1bEVz7lbgtOxnPVdtW
8n3lFktmZQII3/EbHpnVdws=
-----END PRIVATE KEY-----'''

if __name__ == '__main__':
    #import sys;sys.argv = ['', 'Test.test_get_a_broker']
    unittest.main()
