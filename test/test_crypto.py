"""
Created on 7 Dec 2011

@author: will
"""
import unittest
import logging
import os
import tempfile
import shutil

from M2Crypto import X509
from M2Crypto.X509 import X509Error

# hashlib only available in python 2.5+
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from ssm.crypto1 import from_file, \
    file_is_closed, \
    check_cert_key, \
    get_certificate_subject, \
    sign_message, \
    encrypt_message, \
    decrypt_message, \
    verify_message, \
    verify_certificate, \
    verify_certificate_x509, \
    message_hash

# Set up logging - is this necessary?
logging.basicConfig()
log = logging.getLogger('SSM')


class TestEncryptUtils(unittest.TestCase):
    """
    Tests for the encrypt_utils module.
    """
    
    def setUp(self):
        """
        Some of the functions require the certificate and key to be files.
        """
        self.cert_file, self.cert_path = tempfile.mkstemp(prefix='cert')
        os.write(self.cert_file, TEST_CERT)
        os.close(self.cert_file)

        self.key_file, self.key_path = tempfile.mkstemp(prefix='key')
        os.write(self.key_file, TEST_KEY)
        os.close(self.key_file)
        
        # Set up an openssl-style CA directory, containing the 
        # self-signed certificate as its own CA certificate, but with its
        # name as <md5-hash>.0.

        self.ca_dir = tempfile.mkdtemp(prefix='ca')
        hash_name = md5(TEST_CERT).hexdigest() + ".0"
        self.ca_cert_path = os.path.join(self.ca_dir, hash_name)
        self.ca_cert = open(self.ca_cert_path, "w")
        self.ca_cert.write(TEST_CERT)
        self.ca_cert.close()

    def tearDown(self):
        """
        Remove temporary files.
        """
        os.remove(self.cert_path)
        os.remove(self.key_path)
        
        # Remove the CA dir and any contents.
        shutil.rmtree(self.ca_dir)
        
    
    def test_from_file(self):
        """
        Just test that the temporary file that has been set up contains the 
        certificate it should.
        """
        cert = from_file(self.cert_path)
        
        if not cert == TEST_CERT:
            self.fail("The temporary file should include exactly the test certificate.")
    
#    def test_file_is_closed(self):
#        """
#        Test that checking a non-existent file raises an exception, and
#        that open and closed files are detected correctly.
#        
#        I haven't found a good way to implement this method, so the test currently
#        fails.
#        """
#        try: 
#            file_is_closed("o/dev/null")
#        except (IOError, OSError):
#            pass
#        
#        if not file_is_closed(self.cert_path):
#            self.fail("The certificate file shouldn't be open.")
#
#        if file_is_closed("/dev/null"):
#            self.fail("/dev/null is always open.")
        
    def test_check_cert_key(self):
        """
        This will print an error log message for the tests that are 
        supposed to fail; you can ignore it.
        """
        
        # One version of the method would have passed this, because of the
        # way it checked for validity.
        if check_cert_key("hello", "hello"):
            self.fail("Passed an invalid cert and key.")
        
        if check_cert_key("blah", "bloo"):
            self.fail("Passed an invalid cert and key.")
        
        if not check_cert_key(TEST_CERT, TEST_KEY):
            self.fail("Cert and key match but function failed.")
        
    def test_sign_message(self):
        """
        I haven't found a good way to test this yet.  Each time you sign a 
        message, the output has a random element, so you can't compare strings.
        """
        signed = sign_message(MSG, self.cert_path, self.key_path)
        
        
        if not "MIME-Version" in signed:
            self.fail("Didn't get MIME message when signing.")
            
        if not MSG in signed:
            self.fail("The plaintext should be included in the signed message.")
            
        
        # Indirect testing, using the verify_message() method
        retrieved_dn, retrieved_msg = verify_message(signed, self.ca_dir, False)
        
        if not retrieved_dn == TEST_CERT_DN:
            self.fail("The DN of the verified message didn't match the cert.")

        if not retrieved_msg == MSG:
            self.fail("The verified messge didn't match the original.")
            
    def test_verify_message(self):
        
        retrieved_dn, retrieved_msg = verify_message(SAMPLE_SIGNED_MSG, self.ca_dir, False)
        
        if not retrieved_dn == TEST_CERT_DN:
            self.fail("The DN of the verified message didn't match the cert.")
            
            
        if not retrieved_msg == MSG:
            self.fail("The verified messge didn't match the original.")
            
        # Try empty string    
        try:
            verify_message("", self.ca_dir, False)
        except X509Error:
            pass
        # Try rubbish
        try:
            verify_message("Bibbly bobbly", self.ca_dir, False)
        except X509Error:
            pass
        
        
    def test_get_certificate_subject(self):
        """
        Check that the correct DN is extracted from the cert.
        Check that incorrect input gives an appropriate error.
        """
        # Valid certificate
        dn = get_certificate_subject(TEST_CERT)
        
        if not dn == TEST_CERT_DN:
            self.fail("Didn't retrieve correct DN from cert.")
            
        try:
            get_certificate_subject("Rubbish")
        except X509Error:
            pass
        
        try:
            get_certificate_subject("")
        except X509Error:
            pass
        
        
    def test_encrypt_message(self):
        """
        Not a correct test yet.
        """
        encrypted = encrypt_message(MSG, TEST_CERT)
        
        if not "MIME-Version" in encrypted:
            self.fail("Encrypted message is not MIME")
        
        # Indirect testing, using the decrypt_message function.
        decrypted = decrypt_message(encrypted, self.cert_path, self.key_path, self.ca_dir)
        
        if not decrypted == MSG:
            self.fail("Encrypted message wasn't decrypted successfully.")
        
    def test_verify_certificate(self):
        """
        Check that the test certificate is verified against itself, and that
        it doesn't verify without the correct CA directory.  Check that a 
        nonsense string isn't verified.
        
        I can't check the CRLs of a self-signed certificate easily.
        """
        if not verify_certificate(TEST_CERT, self.ca_dir, False):
            self.fail("The self signed certificate should validate against \
            itself in a CA directory.")
            
        if verify_certificate(TEST_CERT, "/tmp", False):
            self.fail("The verify method isn't checking the CA dir correctly.")
            
        try:
            if verify_certificate("bloblo", self.ca_dir, False):
                self.fail("Nonsense successfully verified.")
        except X509Error:
            pass    
 
    def test_verify_certificate_x509(self):
        """
        Simple checks that a loaded X509 object is verified appropriately.
        """
        x509_cert = X509.load_cert_string(TEST_CERT)
        
        if not verify_certificate_x509(x509_cert, self.ca_dir):
            self.fail("The x509 certificate object didn't verify correctly.")
        
        if verify_certificate_x509(x509_cert, "/home"):
            self.fail("The verify method isn't checking the CA dir correctly.")
            
    def test_message_hash(self):
        """
        Simple check that the method does get the MD5 hash.
        """
        test_msg = "This is a test."
        # Pre-calculated hash
        correct_hash = "120ea8a25e5d487bf68b5f7096440019"
        
        calculated_hash = message_hash(test_msg)
        
        if not correct_hash == calculated_hash:
            self.fail("The hash is not correct.") 
            
            
################################################################
# Test data below.
################################################################

TEST_CERT_DN = '/C=uk/ST=oxon/O=stfc/OU=escience/CN=will rogers'

TEST_CERT = """-----BEGIN CERTIFICATE-----
MIICHzCCAYgCCQDmzJkJ04gm+DANBgkqhkiG9w0BAQUFADBUMQswCQYDVQQGEwJ1
azENMAsGA1UECBMEb3hvbjENMAsGA1UEChMEc3RmYzERMA8GA1UECxMIZXNjaWVu
Y2UxFDASBgNVBAMTC3dpbGwgcm9nZXJzMB4XDTExMTIwNzEzNTYyMVoXDTEyMTIw
NjEzNTYyMVowVDELMAkGA1UEBhMCdWsxDTALBgNVBAgTBG94b24xDTALBgNVBAoT
BHN0ZmMxETAPBgNVBAsTCGVzY2llbmNlMRQwEgYDVQQDEwt3aWxsIHJvZ2VyczCB
nzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAxfoCCyKgWyaQla0VLuIannHvwR7A
7zMJk8tze80JOZUPxpFWXhL5F2UJeJtyuHEESp2Sazw4W97nFf25UBVvAbG/TZlz
1YylVq04XgVgQfpAfaL0RF7vsiEAwfxFVz2jqFYol4sZf1SCwoJXsvl54HIxoyeb
Y024ykCglELVePECAwEAATANBgkqhkiG9w0BAQUFAAOBgQCVIVzj4MoQ4MUeloer
9iEDK2V8sRj/BDFQ93cxmiFlsm9k8jENXpGCsOPpO1Q6JjorcXJra+Efb3Prp2Hu
4e4FwyOLuT7Z/CvS5xW0yBIOeoZdqzLFdMV5GhiVZCJCXG+1Sgs3pK4MFb3ySKII
nykY+FuXSOT+seB3K9PSk3dj6w==
-----END CERTIFICATE-----"""
    
TEST_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDF+gILIqBbJpCVrRUu4hqece/BHsDvMwmTy3N7zQk5lQ/GkVZe
EvkXZQl4m3K4cQRKnZJrPDhb3ucV/blQFW8Bsb9NmXPVjKVWrTheBWBB+kB9ovRE
Xu+yIQDB/EVXPaOoViiXixl/VILCgley+XngcjGjJ5tjTbjKQKCUQtV48QIDAQAB
AoGBAKBzplJWBva5A7d7Js7vizldCD5RaXazu5Bf9MGihFZ52+ZIBmKKJ/1w8sMf
4VNgrWS33mIw1VCIEGu/TgB8zpB2UEZVCRYCJgVZa4wsJSVmcprvlqOcOl4qUugF
QkN+f2uG1RT3CbHUV+q0/qnYk5HsU0reaLodaAj9fo8J/OfNAkEA/ntwKVqs/DDk
bFfedYn3oXTf3o6+lmaPkSVtpr+t3zjR2PEJZCIVkiGMow04m/IXZJSyZWnjCq9X
kNdXSGWiBwJBAMcoSwNR24jB8zLI2FLRV74rMwdKqoUc0b3J139Xb87UDW2S9Sdz
N9sJ59TiIut5a49/uiXLiEMQqoGYkORX70cCQBS2Szyyap3kBNNkm3CJmCQF9SqS
B6UKF+lCWJhXxXkDkODNTWxe8c6A+IdUziSzIYBIMfTbF2WJO+FIBYyY6QUCQDcx
EWjAHKjPpwgh5OE+pqRK8H9Kz+rHy9BeyVu+7XtSBM6i9VGTep03J4o1iRvcsFQ6
P2oN95suWTJFB5JgVC0CQDmMynLdOx0KEwgLWXOeeTEqkrZ0l8kIGiaqUhKB45sq
qY6qrtKDPBP08Alm41ruRf5mqdVwL3OqiPe54JLvLEY=
-----END RSA PRIVATE KEY-----"""

MSG = 'This is some test data.'

SAMPLE_ENCRYPTED_MSG = """MIME-Version: 1.0
Content-Disposition: attachment; filename="smime.p7m"
Content-Type: application/pkcs7-mime; smime-type=enveloped-data; name="smime.p7m"
Content-Transfer-Encoding: base64

MIIBbAYJKoZIhvcNAQcDoIIBXTCCAVkCAQAxggENMIIBCQIBADByMGUxCzAJBgNV
BAYTAnVrMRMwEQYDVQQIEwpTb21lLVN0YXRlMQ8wDQYDVQQHEwZkaWRjb3QxDTAL
BgNVBAoTBHN0ZmMxEjAQBgNVBAsTCWUtc2NpZW5jZTENMAsGA1UEAxMEd2lsbAIJ
APQRNeBKQQ7hMA0GCSqGSIb3DQEBAQUABIGAYEQTjh30nvpjMdVci1pkyuMJlZKh
MwuNqlvCM5gpDaXuRV2ILbbe7hY44Wr4m7xIsxtRnaCNsb2HhLOv45hauD3hMqo7
BZva5mZgZZJoWeTLTvrIDfzmttKfyaEd8VgzNU7LN9Pc7d475/BivSkrzz0PWsC2
ia2YJ4Yf8d57vFcwQwYJKoZIhvcNAQcBMBQGCCqGSIb3DQMHBAiwW8i6h01b2oAg
oD8zka5x53cKIh/tunq8684BsnKcqo6qTwKu5EuWoAM=
"""

SAMPLE_SIGNED_MSG = """MIME-Version: 1.0
Content-Type: multipart/signed; protocol="application/pkcs7-signature"; micalg="sha1"; boundary="----F3C4C3F57AECBCA50C586AA0AE28F1CA"

This is an S/MIME signed message

------F3C4C3F57AECBCA50C586AA0AE28F1CA
Content-Type: text/plain

This is some test data.
------F3C4C3F57AECBCA50C586AA0AE28F1CA
Content-Type: application/pkcs7-signature; name="smime.p7s"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="smime.p7s"

MIIEFgYJKoZIhvcNAQcCoIIEBzCCBAMCAQExCzAJBgUrDgMCGgUAMAsGCSqGSIb3
DQEHAaCCAiMwggIfMIIBiAIJAObMmQnTiCb4MA0GCSqGSIb3DQEBBQUAMFQxCzAJ
BgNVBAYTAnVrMQ0wCwYDVQQIEwRveG9uMQ0wCwYDVQQKEwRzdGZjMREwDwYDVQQL
Ewhlc2NpZW5jZTEUMBIGA1UEAxMLd2lsbCByb2dlcnMwHhcNMTExMjA3MTM1NjIx
WhcNMTIxMjA2MTM1NjIxWjBUMQswCQYDVQQGEwJ1azENMAsGA1UECBMEb3hvbjEN
MAsGA1UEChMEc3RmYzERMA8GA1UECxMIZXNjaWVuY2UxFDASBgNVBAMTC3dpbGwg
cm9nZXJzMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDF+gILIqBbJpCVrRUu
4hqece/BHsDvMwmTy3N7zQk5lQ/GkVZeEvkXZQl4m3K4cQRKnZJrPDhb3ucV/blQ
FW8Bsb9NmXPVjKVWrTheBWBB+kB9ovREXu+yIQDB/EVXPaOoViiXixl/VILCgley
+XngcjGjJ5tjTbjKQKCUQtV48QIDAQABMA0GCSqGSIb3DQEBBQUAA4GBAJUhXOPg
yhDgxR6Wh6v2IQMrZXyxGP8EMVD3dzGaIWWyb2TyMQ1ekYKw4+k7VDomOitxcmtr
4R9vc+unYe7h7gXDI4u5Ptn8K9LnFbTIEg56hl2rMsV0xXkaGJVkIkJcb7VKCzek
rgwVvfJIogifKRj4W5dI5P6x4Hcr09KTd2PrMYIBuzCCAbcCAQEwYTBUMQswCQYD
VQQGEwJ1azENMAsGA1UECBMEb3hvbjENMAsGA1UEChMEc3RmYzERMA8GA1UECxMI
ZXNjaWVuY2UxFDASBgNVBAMTC3dpbGwgcm9nZXJzAgkA5syZCdOIJvgwCQYFKw4D
AhoFAKCBsTAYBgkqhkiG9w0BCQMxCwYJKoZIhvcNAQcBMBwGCSqGSIb3DQEJBTEP
Fw0xMjAxMTAxMTUxMDBaMCMGCSqGSIb3DQEJBDEWBBR1ImJfwBg8hODih8d7O4+l
Um+FyTBSBgkqhkiG9w0BCQ8xRTBDMAoGCCqGSIb3DQMHMA4GCCqGSIb3DQMCAgIA
gDANBggqhkiG9w0DAgIBQDAHBgUrDgMCBzANBggqhkiG9w0DAgIBKDANBgkqhkiG
9w0BAQEFAASBgKbM42pthzMpgt/iFFz8ltn216JZiRf6sdud5WEmDLJ326Co1jcW
++PGdzOmxUjlU1ncGZ1FX0K3DW91j6z+W257++/e5oBhpPSQm0Qjuez0RkJXOgEr
S2DikUAt2ztVIBEbPtTe76euH+XLzO+Zhuy8SVurxOYLcRE8NiCSb4fO

------F3C4C3F57AECBCA50C586AA0AE28F1CA--
"""


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
