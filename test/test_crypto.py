from __future__ import print_function

import logging
import OpenSSL
import os
import quopri
from subprocess import call, Popen, PIPE
import tempfile
import unittest

from ssm.crypto import (check_cert_key,
    get_certificate_subject,
    get_signer_cert,
    sign,
    encrypt,
    decrypt,
    verify,
    verify_cert,
    _get_subject_components,
    CryptoException
)


logging.basicConfig()


class TestEncryptUtils(unittest.TestCase):
    '''
    Tests for the encrypt_utils module.
    '''

    def setUp(self):
        '''
        If no key/cert pair found, generate a new
        key/cert pair and store as a file.
        '''
        # create a key/cert pair
        call(['openssl', 'req', '-x509', '-nodes', '-days', '1',
              '-newkey', 'rsa:2048', '-keyout', TEST_KEY_FILE,
              '-out', TEST_CERT_FILE, '-subj', TEST_CERT_DN])

        # Set up an openssl-style CA directory, containing the
        # self-signed certificate as its own CA certificate, but with its
        # name as <hash-of-subject-DN>.0.
        p1 = Popen(['openssl', 'x509', '-subject_hash', '-noout'],
                   stdin=PIPE, stdout=PIPE, stderr=PIPE,
                   universal_newlines=True)

        with open(TEST_CERT_FILE, 'r') as test_cert:
            cert_string = test_cert.read()

        hash_name, _unused_error = p1.communicate(cert_string)

        self.ca_certpath = os.path.join(TEST_CA_DIR, hash_name.strip() + '.0')
        with open(self.ca_certpath, 'w') as ca_cert:
            ca_cert.write(cert_string)

    def tearDown(self):
        '''Remove temporary files.'''
        os.remove(TEST_CERT_FILE)
        os.remove(TEST_KEY_FILE)
        os.remove(self.ca_certpath)

    def test_check_cert_key(self):
        """Check that valid cert and key works."""
        self.assertTrue(check_cert_key(TEST_CERT_FILE, TEST_KEY_FILE),
                        'Cert and key match but function failed.')

    def test_check_cert_key_invalid_paths(self):
        """Check invalid file paths don't return True."""
        self.assertFalse(check_cert_key('hello', 'hello'),
                         'Accepted invalid file paths.')
        self.assertFalse(check_cert_key(TEST_CERT_FILE, 'k'),
                         'Accepted invalid key path.')
        self.assertFalse(check_cert_key('c', TEST_KEY_FILE),
                         'Accepted invalid cert path.')

    def test_check_cert_key_arg_order(self):
        """Check incorrect order of cert and key path args doesn't succeed."""
        self.assertFalse(check_cert_key(TEST_CERT_FILE, TEST_CERT_FILE),
                         'Accepted certificate as key.')
        self.assertFalse(check_cert_key(TEST_KEY_FILE, TEST_KEY_FILE),
                         'Accepted key as cert.')
        self.assertFalse(check_cert_key(TEST_KEY_FILE, TEST_CERT_FILE),
                         'Accepted key and cert wrong way round.')

    def test_check_cert_key_invalid_files(self):
        """Check behaviour with an invalid cert or key file."""
        with tempfile.NamedTemporaryFile() as tmp:
            self.assertFalse(check_cert_key(tmp.name, TEST_KEY_FILE),
                             'Accepted invalid cert file.')
            self.assertFalse(check_cert_key(TEST_CERT_FILE, tmp.name),
                             'Accepted invalid key file.')

    def test_sign(self):
        '''
        I haven't found a good way to test this yet.  Each time you sign a
        message, the output has a random element, so you can't compare strings.
        '''
        signed = sign(MSG, TEST_CERT_FILE, TEST_KEY_FILE)

        if 'MIME-Version' not in signed:
            self.fail("Didn't get MIME message when signing.")

        if MSG not in signed:
            self.fail('The plaintext should be included in the signed message.')

        # Indirect testing, using the verify_message() method
        retrieved_msg, retrieved_dn = verify(signed, TEST_CA_DIR, False)

        self.assertEqual(
            retrieved_dn, TEST_CERT_DN,
            "The DN of the verified message didn't match the cert.")

        self.assertEqual(retrieved_msg, MSG,
                         "The verified message didn't match the original.")

    def test_verify(self):

        signed_msg = sign(MSG, TEST_CERT_FILE, TEST_KEY_FILE)

        # This is a manual 'fudge' to make MS2 appear like a
        # quoted-printable message when signed
        # Encode MSG2 so it's 'quoted-printable', after encoding it to ensure
        # it's a bytes object for Python 3. Latter is a no-op in Python 2.
        quopri_msg = quopri.encodestring(MSG2.encode())

        # In Python 3, encodestring() returns bytes so decode to a string while
        # Python 2 compatability is still required.
        if not isinstance(quopri_msg, str):
            quopri_msg = quopri_msg.decode()

        # Add Content-Type and Content-Transfer-Encoding
        # headers to message
        header_quopri_msg = ('Content-Type: text/xml; charset=utf8\n'
                             'Content-Transfer-Encoding: quoted-printable\n'
                             '\n'
                             '%s' % quopri_msg)

        # We can't use crypto.sign as that assumes the use of the '-text' option
        # which cause the message to be interpreted as plaintext
        p1 = Popen(['openssl', 'smime', '-sign', '-inkey', TEST_KEY_FILE, '-signer', TEST_CERT_FILE],
                   stdin=PIPE, stdout=PIPE, stderr=PIPE,
                   universal_newlines=True)

        signed_msg2, error = p1.communicate(header_quopri_msg)

        if error != '':
            self.fail(error)

        retrieved_msg, retrieved_dn = verify(signed_msg, TEST_CA_DIR, False)

        self.assertEqual(
            retrieved_dn, TEST_CERT_DN,
            "The DN of the verified message didn't match the cert.")

        self.assertEqual(
            retrieved_msg.strip(), MSG,
            "The verified messge didn't match the original.")

        retrieved_msg2, retrieved_dn2 = verify(signed_msg2, TEST_CA_DIR, False)

        self.assertEqual(
            retrieved_dn2, TEST_CERT_DN,
            "The DN of the verified message didn't match the cert.")

        self.assertEqual(
            retrieved_msg2.strip(), MSG2,
            "The verified messge didn't match the original.")

        # Try empty string
        self.assertRaises(CryptoException, verify, '', TEST_CA_DIR, False)
        # Try rubbish
        self.assertRaises(CryptoException, verify, 'Bibbly bobbly', TEST_CA_DIR, False)
        # Try None arguments
        self.assertRaises(CryptoException, verify, 'Bibbly bobbly', None, False)
        self.assertRaises(CryptoException, verify, None, 'not a path', False)

    def test_get_subject_components(self):
        """Check that the correct DN is extracted from the certstring."""
        # Still a valid certificate
        with open(TEST_CERT_FILE, 'r') as test_cert:
            cert_string = test_cert.read()

        subject_x509name = OpenSSL.crypto.load_certificate(
                OpenSSL.crypto.FILETYPE_PEM, cert_string
        ).get_subject()

        self.assertEqual(_get_subject_components(subject_x509name), TEST_CERT_DN,
                         msg="Didn't retrieve correct DN from cert.")

    def test_get_certificate_subject(self):
        '''
        Check that the correct DN is extracted from the cert.
        Check that incorrect input gives an appropriate error.
        '''
        # Valid certificate
        with open(TEST_CERT_FILE, 'r') as test_cert:
            cert_string = test_cert.read()
        dn = get_certificate_subject(cert_string)

        if not dn == TEST_CERT_DN:
            self.fail("Didn't retrieve correct DN from cert.")

        self.assertRaises(CryptoException, get_certificate_subject, 'Rubbish')

        self.assertRaises(CryptoException, get_certificate_subject, '')

    def test_get_signer_cert(self):
        '''
        Check that the certificate retrieved from the signed message
        matches the certificate used to sign it.
        '''
        signed_msg = sign(MSG, TEST_CERT_FILE, TEST_KEY_FILE)

        cert = get_signer_cert(signed_msg)
        # Remove any information preceding the encoded certificate.
        cert = cert[cert.find('-----BEGIN'):]

        with open(TEST_CERT_FILE, 'r') as test_cert:
            cert_string = test_cert.read()

        if cert.strip() != cert_string.strip():
            self.fail('Certificate retrieved from signature '
                      'does not match certificate used to sign.')

    def test_encrypt(self):
        '''
        Not a correct test yet.
        '''
        encrypted = encrypt(MSG, TEST_CERT_FILE)

        if 'MIME-Version' not in encrypted:
            self.fail('Encrypted message is not MIME')

        # Indirect testing, using the decrypt_message function.
        decrypted = decrypt(encrypted, TEST_CERT_FILE, TEST_KEY_FILE)

        if decrypted != MSG:
            self.fail("Encrypted message wasn't decrypted successfully.")

        # invalid cipher
        self.assertRaises(CryptoException, encrypt, MSG, TEST_CERT_FILE, 'aes1024')


    def test_decrypt(self):
        '''
        Check that the encrypted message can be decrypted and returns the
        original message.
        '''
        encrypted = encrypt(MSG, TEST_CERT_FILE)
        decrypted = decrypt(encrypted, TEST_CERT_FILE, TEST_KEY_FILE)

        if decrypted.strip() != MSG:
            self.fail('Failed to decrypt message.')


    def test_verify_cert(self):
        '''
        Check that the test certificate is verified against itself, and that
        it doesn't verify without the correct CA directory.  Check that a
        nonsense string isn't verified.

        I can't check the CRLs of a self-signed certificate easily.
        '''
        with open(TEST_CERT_FILE, 'r') as test_cert:
            cert_string = test_cert.read()

        if not verify_cert(cert_string, TEST_CA_DIR, False):
            self.fail('The self signed certificate should validate against'
                      'itself in a CA directory.')

        if verify_cert(cert_string, '/var/tmp', False):
            self.fail("The verify method isn't checking the CA dir correctly.")

        if verify_cert('bloblo', TEST_CA_DIR, False):
            self.fail('Nonsense successfully verified.')

        if verify_cert(cert_string, TEST_CA_DIR, True):
            self.fail('The self-signed certificate should not be verified ' +
                      'if CRLs are checked.')

        self.assertRaises(CryptoException, verify_cert, None, TEST_CA_DIR, False)

    def test_message_tampering(self):
        """Test that a tampered message is not accepted as valid."""
        signed_message = sign(MSG, TEST_CERT_FILE, TEST_KEY_FILE)
        tampered_message = signed_message.replace(MSG, "Spam")

        # Verifying the orignal, un-tampered message should be fine.
        verified_message, verified_signer = verify(
            signed_message, TEST_CA_DIR, False
        )
        self.assertEqual(verified_message, MSG)
        self.assertEqual(verified_signer, TEST_CERT_DN)

        # Verifying the tampered message should not be fine.
        self.assertRaises(
            CryptoException, verify, tampered_message, TEST_CA_DIR, False
        )

################################################################
# Test data below.
################################################################

TEST_CERT_DN = '/C=UK/O=STFC/OU=SC/CN=Test Cert'

TEST_CERT_FILE = '/tmp/test.crt'

TEST_KEY_FILE = '/tmp/test.key'

TEST_CA_DIR='/tmp'

MSG = 'This is some test data.'

MSG2 = '''<com:UsageRecord xmlns:com="http://eu-emi.eu/namespaces/2012/11/computerecord"><com:RecordIdentity com:recordId="62991a08-909b-4516-aa30-3732ab3d8998" com:createTime="2013-02-22T15:58:44.567+01:00"/><com:JobIdentity><com:GlobalJobId>ac2b1157-7aff-42d9-945e-389aa9bbb19a</com:GlobalJobId><com:LocalJobId>7005</com:LocalJobId></com:JobIdentity><com:UserIdentity><com:GlobalUserName com:type="rfc2253">CN=Bjoern Hagemeier,OU=Forschungszentrum Juelich GmbH,O=GridGermany,C=DE</com:GlobalUserName><com:LocalUserId>bjoernh</com:LocalUserId><com:LocalGroup>users</com:LocalGroup></com:UserIdentity><com:JobName>HiLA</com:JobName><com:Status>completed</com:Status><com:ExitStatus>0</com:ExitStatus><com:Infrastructure com:type="grid"/><com:Middleware com:name="unicore">unicore</com:Middleware><com:WallDuration>PT0S</com:WallDuration><com:CpuDuration>PT0S</com:CpuDuration><com:ServiceLevel com:type="HEPSPEC">1.0</com:ServiceLevel><com:Memory com:metric="total" com:storageUnit="KB" com:type="physical">0</com:Memory><com:Memory com:metric="total" com:storageUnit="KB" com:type="shared">0</com:Memory><com:TimeInstant com:type="uxToBssSubmitTime">2013-02-22T15:58:44.568+01:00</com:TimeInstant><com:TimeInstant com:type="uxStartTime">2013-02-22T15:58:46.563+01:00</com:TimeInstant><com:TimeInstant com:type="uxEndTime">2013-02-22T15:58:49.978+01:00</com:TimeInstant><com:TimeInstant com:type="etime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant com:type="ctime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant com:type="qtime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant com:type="maxWalltime">2013-02-22T16:58:45+01:00</com:TimeInstant><com:NodeCount>1</com:NodeCount><com:Processors>2</com:Processors><com:EndTime>2013-02-22T15:58:45+01:00</com:EndTime><com:StartTime>2013-02-22T15:58:45+01:00</com:StartTime><com:MachineName>zam052v15.zam.kfa-juelich.de</com:MachineName><com:SubmitHost>zam052v02</com:SubmitHost><com:Queue com:description="execution">batch</com:Queue><com:Site>zam052v15.zam.kfa-juelich.de</com:Site><com:Host com:primary="false" com:description="CPUS=2;SLOTS=1,0">zam052v15</com:Host></com:UsageRecord>'''

if __name__ == '__main__':
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
