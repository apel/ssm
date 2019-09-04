from __future__ import print_function

import os
import shutil
import tempfile
import unittest
from subprocess import call

from ssm.message_directory import MessageDirectory
from ssm.ssm2 import Ssm2, Ssm2Exception


class TestSsm(unittest.TestCase):
    '''
    Class used for testing SSM.
    '''

    def setUp(self):
        """Set up a test directory and certificates."""
        self._tmp_dir = tempfile.mkdtemp(prefix='ssm')

        # Some functions require the hardcoded expired certificate and
        # key to be files.
        key_fd, self._key_path = tempfile.mkstemp(prefix='key',
                                                  dir=self._tmp_dir)
        os.write(key_fd, TEST_KEY)
        os.close(key_fd)

        cert_fd, self._expired_cert_path = tempfile.mkstemp(prefix='cert',
                                                            dir=self._tmp_dir)
        os.write(cert_fd, EXPIRED_CERT)
        os.close(cert_fd)

        self.valid_dn_file, self.valid_dn_path = tempfile.mkstemp(
            prefix='valid', dir=self._tmp_dir)
        os.write(self.valid_dn_file, '/test/dn')
        os.close(self.valid_dn_file)

        # Create a new certificate using the hardcoded key.
        # The subject has been hardcoded so that the generated
        # certificate subject matches the subject of the hardcoded,
        # expired, certificate at the bottom of this file.
        # 2 days used so that verify_cert_date doesn't think it expires soon.
        call(['openssl', 'req', '-x509', '-nodes', '-days', '2', '-new',
              '-key', self._key_path, '-out', TEST_CERT_FILE,
              '-subj', '/C=UK/O=STFC/OU=SC/CN=Test Cert'])

        self._brokers = [('not.a.broker', 123)]
        self._capath = '/not/a/path'
        self._check_crls = False
        self._pidfile = self._tmp_dir + '/pidfile'

        self._listen = '/topic/test'
        self._dest = '/topic/test'

        self._msgdir = tempfile.mkdtemp(prefix='msgq')

    def tearDown(self):
        """Remove test directory and all contents."""
        try:
            shutil.rmtree(self._msgdir)
            shutil.rmtree(self._tmp_dir)
        except OSError as e:
            print('Error removing temporary directory %s' % self._tmp_dir)
            print(e)

    def test_on_message(self):
        '''
        This is quite a complicated method, so it would take a long time
        to write a comprehensive test.  Instead, I will start with where there
        might be problems.
        '''
        test_ssm = Ssm2(self._brokers, self._msgdir, TEST_CERT_FILE,
                        self._key_path, dest=self._dest, listen=self._listen)
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

        # Check that message with ID of 'ping' doesn't raise an exception.
        # Messages with this ID are handled differently to normal messages.
        test_ssm.on_message({'empa-id': 'ping'}, 'body')
        # Check that msg with ID and no real content doesn't raise exception.
        test_ssm.on_message({'empa-id': '012345'}, 'body')

    def test_init_expired_cert(self):
        """Test right exception is thrown creating an SSM with expired cert."""
        expected_error = ('Certificate %s has expired or will expire '
                          'within a day.' % self._expired_cert_path)
        try:
            # Indirectly test crypto.verify_cert_date
            Ssm2(self._brokers, self._msgdir, self._expired_cert_path,
                 self._key_path, listen=self._listen)
        except Ssm2Exception as error:
            if str(error) != expected_error:
                self.fail('Raised: "%s" Expected: "%s"' % (error,
                                                           expected_error))
            else:
                return

        # If the test gets here, then it has failed as no exception was thrown.
        self.fail('An SSM instance was created with an expired certificate!')

    def test_init_expired_server_cert(self):
        """Check that exception is raised if server cert has expired."""
        self.assertRaises(
            Ssm2Exception, Ssm2, self._brokers, self._msgdir, TEST_CERT_FILE,
            self._key_path, dest=self._dest, enc_cert=self._expired_cert_path,
            verify_enc_cert=False
        )
        # verify_enc_cert is set to False as we don't want to risk raising an
        # exception by failing cert verification.

    def test_ssm_init_non_dirq(self):
        """Test a SSM can be initialised with support for non-dirq sending."""
        try:
            ssm = Ssm2(self._brokers, self._msgdir, TEST_CERT_FILE,
                       self._key_path, dest=self._dest, listen=None,
                       path_type='directory')
        except Ssm2Exception as error:
            self.fail('An error occured trying to create an SSM using '
                      'the non-dirq functionality: %s.' % error)

        # Assert the outbound queue is of the expected type.
        self.assertTrue(isinstance(ssm._outq, MessageDirectory))


TEST_CERT_FILE = '/tmp/test.crt'

# As we want the expired certifcate to match the key used, we can't
# generate them on the fly. The cert below has the subject:
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
# certificates generated by the test methods.
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
    unittest.main()
