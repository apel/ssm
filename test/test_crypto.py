'''
Created on 7 Dec 2011

@author: will
'''
import unittest
import logging
import os
import tempfile
import shutil
from subprocess import Popen, PIPE

from ssm.crypto import _from_file, \
    check_cert_key, \
    get_certificate_subject, \
    get_signer_cert, \
    sign, \
    encrypt, \
    decrypt, \
    verify, \
    verify_cert, \
    CryptoException

# Set up logging - is this necessary?
logging.basicConfig()
log = logging.getLogger('SSM')


class TestEncryptUtils(unittest.TestCase):
    '''
    Tests for the encrypt_utils module.
    '''
    
    def setUp(self):
        '''
        Some of the functions require the certificate and key to be files.
        '''
        self.certfile, self.certpath = tempfile.mkstemp(prefix='cert')
        os.write(self.certfile, TEST_CERT)
        os.close(self.certfile)

        self.keyfile, self.keypath = tempfile.mkstemp(prefix='key')
        os.write(self.keyfile, TEST_KEY)
        os.close(self.keyfile)
        
        # Set up an openssl-style CA directory, containing the 
        # self-signed certificate as its own CA certificate, but with its
        # name as <hash-of-subject-DN>.0.

        self.ca_dir = tempfile.mkdtemp(prefix='ca')
        p1 = Popen(['openssl', 'x509', '-subject_hash', '-noout'],
                   stdin=PIPE, stdout=PIPE, stderr=PIPE)
        hash_name, unused_error = p1.communicate(TEST_CERT)
        self.ca_certpath = os.path.join(self.ca_dir, hash_name.strip() + '.0')
        self.ca_cert = open(self.ca_certpath, 'w')
        self.ca_cert.write(TEST_CERT)
        self.ca_cert.close()

    def tearDown(self):
        '''
        Remove temporary files.
        '''
        os.remove(self.certpath)
        os.remove(self.keypath)
        
        # Remove the CA dir and any contents.
        shutil.rmtree(self.ca_dir)
        
    
    def test_from_file(self):
        '''
        Just test that the temporary file that has been set up contains the 
        certificate it should.
        '''
        cert = _from_file(self.certpath)
        
        if not cert == TEST_CERT:
            self.fail('The temporary file should include exactly the test certificate.')
    
    def test_check_cert_key(self):
        '''
        This will print an error log message for the tests that are 
        supposed to fail; you can ignore it.
        '''
        
        # One version of the method would have passed this, because of the
        # way it checked for validity.
        try:
            if check_cert_key('hello', 'hello'):
                self.fail('Accepted non-existent cert and key.')
        except CryptoException:
            pass
        
        if check_cert_key(self.certpath, self.certpath):
            self.fail('Accepted certificate as key.')
        
        if not check_cert_key(self.certpath, self.keypath):
            self.fail('Cert and key match but function failed.')
        
    def test_sign(self):
        '''
        I haven't found a good way to test this yet.  Each time you sign a 
        message, the output has a random element, so you can't compare strings.
        '''
        signed = sign(MSG, self.certpath, self.keypath)
        
        if not 'MIME-Version' in signed:
            self.fail("Didn't get MIME message when signing.")
            
        if not MSG in signed:
            self.fail('The plaintext should be included in the signed message.')
        
        # Indirect testing, using the verify_message() method
        retrieved_msg, retrieved_dn = verify(signed, self.ca_dir, False)
        
        if not retrieved_dn == TEST_CERT_DN:
            self.fail("The DN of the verified message didn't match the cert.")

        if not retrieved_msg == MSG:
            self.fail("The verified messge didn't match the original.")
            
    def test_verify(self):
        
        retrieved_msg, retrieved_dn = verify(SIGNED_MSG, self.ca_dir, False)
        
        if not retrieved_dn == TEST_CERT_DN:
            self.fail("The DN of the verified message didn't match the cert.")
            
            
        if not retrieved_msg.strip() == MSG:
            self.fail("The verified messge didn't match the original.")
            
        # Try empty string    
        try:
            verify('', self.ca_dir, False)
        except CryptoException:
            pass
        # Try rubbish
        try:
            verify('Bibbly bobbly', self.ca_dir, False)
        except CryptoException:
            pass
        # Try None arguments 
        try:
            verify('Bibbly bobbly', None, False)
        except CryptoException:
            pass
        try:
            verify(None, 'not a path', False)
        except CryptoException:
            pass
        
    def test_get_certificate_subject(self):
        '''
        Check that the correct DN is extracted from the cert.
        Check that incorrect input gives an appropriate error.
        '''
        # Valid certificate
        dn = get_certificate_subject(TEST_CERT)
        
        if not dn == TEST_CERT_DN:
            self.fail("Didn't retrieve correct DN from cert.")
            
        try:
            subj = get_certificate_subject('Rubbish')
            self.fail('Returned %s as subject from empty string.' % subj)
        except CryptoException:
            pass
        
        try:
            subj = get_certificate_subject('')
            self.fail('Returned %s as subject from empty string.' % subj)
        except CryptoException:
            pass
        
    def test_get_signer_cert(self):
        '''
        Check that the certificate retrieved from the signed message
        matches the certificate used to sign it.
        '''
        cert = get_signer_cert(SIGNED_MSG)
        # Remove any information preceding the encoded certificate.
        cert = cert[cert.find('-----BEGIN'):]
        
        if cert.strip() != TEST_CERT:
            self.fail('Certificate retrieved from signature does not match \
                    certificate used to sign.')
        
    def test_encrypt(self):
        '''
        Not a correct test yet.
        '''
        encrypted = encrypt(MSG, self.certpath)
        
        if not 'MIME-Version' in encrypted:
            self.fail('Encrypted message is not MIME')
        
        # Indirect testing, using the decrypt_message function.
        decrypted = decrypt(encrypted, self.certpath, self.keypath)
        
        if decrypted != MSG:
            self.fail("Encrypted message wasn't decrypted successfully.")
            
    def test_decrypt(self):
        '''
        Check that the encrypted message can be decrypted and returns the
        original message.
        '''
        decrypted = decrypt(ENCRYPTED_MSG, self.certpath, self.keypath)
        
        if decrypted.strip() != MSG:
            self.fail('Failed to decrypt message.') 
        
        
    def test_verify_cert(self):
        '''
        Check that the test certificate is verified against itself, and that
        it doesn't verify without the correct CA directory.  Check that a 
        nonsense string isn't verified.
        
        I can't check the CRLs of a self-signed certificate easily.
        '''
        if not verify_cert(TEST_CERT, self.ca_dir, False):
            self.fail('The self signed certificate should validate against \
            itself in a CA directory.')
            
        if verify_cert(TEST_CERT, '/tmp', False):
            self.fail("The verify method isn't checking the CA dir correctly.")
            
        if verify_cert('bloblo', self.ca_dir, False):
            self.fail('Nonsense successfully verified.')
 
            
################################################################
# Test data below.
################################################################

TEST_CERT_DN = '/C=uk/ST=Some-State/O=stfc/OU=sc/CN=will rogers'

TEST_CERT = '''-----BEGIN CERTIFICATE-----
MIICHzCCAYgCCQC4/1HG8oLPdzANBgkqhkiG9w0BAQsFADBUMQswCQYDVQQGEwJ1
azETMBEGA1UECAwKU29tZS1TdGF0ZTENMAsGA1UECgwEc3RmYzELMAkGA1UECwwC
c2MxFDASBgNVBAMMC3dpbGwgcm9nZXJzMB4XDTEyMDgzMTA4MzMzMFoXDTEzMDgz
MTA4MzMzMFowVDELMAkGA1UEBhMCdWsxEzARBgNVBAgMClNvbWUtU3RhdGUxDTAL
BgNVBAoMBHN0ZmMxCzAJBgNVBAsMAnNjMRQwEgYDVQQDDAt3aWxsIHJvZ2VyczCB
nzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAwV+3d/cVmMa/EgKbIjLJ7Xw49rqi
OGFgERwsEab8qH9AHNuJPEWIG2Mqc6JCefyDm1vAmFpI6s7LTNmk/Xa6yOOGCOqY
MTGCb3KpnQE24xM6rgHEMxH11FjiboKueV+IbSC7iNXH8GxuPhE7buaGJ9jQU+Ky
WxWpBiDe8xRs0KcCAwEAATANBgkqhkiG9w0BAQsFAAOBgQBzZx35HwUPzlnjx12Q
C394M6HRs2e09woMb2jimgyS1lL3UtZ7Mw8rmlPwL79m/Ez3Q/232im99HGMtEXe
gDxVeVCZtrL9vh9WESidGMOfjE18GtS/oly5TuBiIaFr0qaHUVdHyXFPepMtebY/
J+IH3JWOuaPmEnfxzzwiASjkAg==
-----END CERTIFICATE-----'''
    
TEST_KEY = '''-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQDBX7d39xWYxr8SApsiMsntfDj2uqI4YWARHCwRpvyof0Ac24k8
RYgbYypzokJ5/IObW8CYWkjqzstM2aT9drrI44YI6pgxMYJvcqmdATbjEzquAcQz
EfXUWOJugq55X4htILuI1cfwbG4+ETtu5oYn2NBT4rJbFakGIN7zFGzQpwIDAQAB
AoGBAJ+HysGiy2Nt26YNFlUBV4ugJxKN6FThKLMU7dpmTBzqVkc4aqCZsG7/wb8C
BxvCUgTyjhJisbNdhWVSTQZ6VB8FkFC9EEDdFoCPUi69ran1loa53pElABVyH2w7
WcS4lplPLjpmG55IqZy+CWdG30YEr4fCssZwbIGdijB2AQBxAkEA7S/O9cR6lKvX
7mWSrCcaR9sCXdiU12SmihnM2LsuGtXcSC7Jx9xnly+6PyeoNVTw1M/3F2G5LNTJ
cBj6dT2qGQJBANC2RFj70WfYCaRYgRB+gF5ky/3lSZmOkWK/uAN1UV17p/LHRXAQ
dIOsI60UDJ2HzUp/CXbWctbYplgXF/hvKL8CQHG0q6jSillfkGLvOsNg845jBd1r
iN9Blz05ZSS5hz7CK5pHI+C2XsrxzH2eS1tV3yaGlFQXOyis0ez1bIxsBXECQQCl
zIVTIwhhNA/EzMIKtlOHqQ8cLO9g2w7HoYGuzZ3LY5YxmPeiZJAKoc7diZXT9rOw
wGZmT0l/PzA1vnK+Wp/FAkBERPL/ry6jwr5eZTRUrgPNUjzGbMp46kbiBl9I4yWN
ba7gkcCbglQsQdB0tSrExAeR0dqym9SAzqkdRf/dJCfX
-----END RSA PRIVATE KEY-----'''

MSG = 'This is some test data.'

ENCRYPTED_MSG = '''MIME-Version: 1.0
Content-Disposition: attachment; filename="smime.p7m"
Content-Type: application/x-pkcs7-mime; smime-type=enveloped-data; name="smime.p7m"
Content-Transfer-Encoding: base64

MIIBXwYJKoZIhvcNAQcDoIIBUDCCAUwCAQAxgfswgfgCAQAwYTBUMQswCQYDVQQG
EwJ1azETMBEGA1UECAwKU29tZS1TdGF0ZTENMAsGA1UECgwEc3RmYzELMAkGA1UE
CwwCc2MxFDASBgNVBAMMC3dpbGwgcm9nZXJzAgkAuP9RxvKCz3cwDQYJKoZIhvcN
AQEBBQAEgYAywxFQtRJJ8rpGnh+X6V2O59lYSQwL5IQXxLEfsP8HKr7i4RSTEloT
BZMi2s56hPuBAYYI4KloK6FIzbtqCYIOb9co/hEoaurKT/82zQqLyKkpR8W0jJEm
mIxCz5+n21FPTKh5TRUjmXWdCrXyPaV/f0jVWzluJgAUE5Hzfsq46TBJBgkqhkiG
9w0BBwEwGgYIKoZIhvcNAwIwDgICAKAECKNL0EuCiLR9gCCoeY/bQ/h8WkPlFNYL
rkMwpW1VA80ij9O8eTjxpHaycw==
'''

SIGNED_MSG = '''MIME-Version: 1.0
Content-Type: multipart/signed; protocol="application/x-pkcs7-signature"; micalg="sha1"; boundary="----1C12AE3B24C506C96BF5DE14FAB740A7"

This is an S/MIME signed message

------1C12AE3B24C506C96BF5DE14FAB740A7
Content-Type: text/plain

This is some test data.

------1C12AE3B24C506C96BF5DE14FAB740A7
Content-Type: application/x-pkcs7-signature; name="smime.p7s"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="smime.p7s"

MIIEPQYJKoZIhvcNAQcCoIIELjCCBCoCAQExCzAJBgUrDgMCGgUAMAsGCSqGSIb3
DQEHAaCCAiMwggIfMIIBiAIJALj/Ucbygs93MA0GCSqGSIb3DQEBCwUAMFQxCzAJ
BgNVBAYTAnVrMRMwEQYDVQQIDApTb21lLVN0YXRlMQ0wCwYDVQQKDARzdGZjMQsw
CQYDVQQLDAJzYzEUMBIGA1UEAwwLd2lsbCByb2dlcnMwHhcNMTIwODMxMDgzMzMw
WhcNMTMwODMxMDgzMzMwWjBUMQswCQYDVQQGEwJ1azETMBEGA1UECAwKU29tZS1T
dGF0ZTENMAsGA1UECgwEc3RmYzELMAkGA1UECwwCc2MxFDASBgNVBAMMC3dpbGwg
cm9nZXJzMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDBX7d39xWYxr8SApsi
MsntfDj2uqI4YWARHCwRpvyof0Ac24k8RYgbYypzokJ5/IObW8CYWkjqzstM2aT9
drrI44YI6pgxMYJvcqmdATbjEzquAcQzEfXUWOJugq55X4htILuI1cfwbG4+ETtu
5oYn2NBT4rJbFakGIN7zFGzQpwIDAQABMA0GCSqGSIb3DQEBCwUAA4GBAHNnHfkf
BQ/OWePHXZALf3gzodGzZ7T3CgxvaOKaDJLWUvdS1nszDyuaU/Avv2b8TPdD/bfa
Kb30cYy0Rd6APFV5UJm2sv2+H1YRKJ0Yw5+MTXwa1L+iXLlO4GIhoWvSpodRV0fJ
cU96ky15tj8n4gfclY65o+YSd/HPPCIBKOQCMYIB4jCCAd4CAQEwYTBUMQswCQYD
VQQGEwJ1azETMBEGA1UECAwKU29tZS1TdGF0ZTENMAsGA1UECgwEc3RmYzELMAkG
A1UECwwCc2MxFDASBgNVBAMMC3dpbGwgcm9nZXJzAgkAuP9RxvKCz3cwCQYFKw4D
AhoFAKCB2DAYBgkqhkiG9w0BCQMxCwYJKoZIhvcNAQcBMBwGCSqGSIb3DQEJBTEP
Fw0xMzAxMDIxNDI5MzZaMCMGCSqGSIb3DQEJBDEWBBS4mGqHlYCOu0+aUiwPuT3+
Q8yGEDB5BgkqhkiG9w0BCQ8xbDBqMAsGCWCGSAFlAwQBKjALBglghkgBZQMEARYw
CwYJYIZIAWUDBAECMAoGCCqGSIb3DQMHMA4GCCqGSIb3DQMCAgIAgDANBggqhkiG
9w0DAgIBQDAHBgUrDgMCBzANBggqhkiG9w0DAgIBKDANBgkqhkiG9w0BAQEFAASB
gFxj4avIK5BI4c4dEvgIwfoafSUMWjd69yvmIWFBpJ3zorziiU4Bk935FoyfsaUI
3O93S+wZ5LcANTjQ5SFsRR5dNao9TsNBt1HFhEf6ozuDMWml22vEi8ImeBBgQjY0
SxVQz6HXV3PGNS3QsSreRd75rOrteKRT9RIo/exuFCUB

------1C12AE3B24C506C96BF5DE14FAB740A7--'''


if __name__ == '__main__':
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
