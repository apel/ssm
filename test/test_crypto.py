'''
Created on 7 Dec 2011

@author: will
'''
import unittest
import logging
import os
import tempfile
import shutil
from subprocess import call, Popen, PIPE

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
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)

        with open(TEST_CERT_FILE, 'r') as test_cert:
            cert_string = test_cert.read()

        hash_name, unused_error = p1.communicate(cert_string)

        self.ca_certpath = os.path.join(TEST_CA_DIR, hash_name.strip() + '.0')
        with open(self.ca_certpath, 'w') as ca_cert:
            ca_cert.write(cert_string)

    def tearDown(self):
        '''Remove temporary files.'''
        os.remove(TEST_CERT_FILE)
        os.remove(TEST_KEY_FILE)
        os.remove(self.ca_certpath)

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
            self.fail("The verified message didn't match the original.")
            
    def test_verify(self):
        
        retrieved_msg, retrieved_dn = verify(SIGNED_MSG, self.ca_dir, False)
        
        if not retrieved_dn == TEST_CERT_DN:
            self.fail("The DN of the verified message didn't match the cert.")
            
        if not retrieved_msg.strip() == MSG:
            self.fail("The verified messge didn't match the original.")
            
        retrieved_msg2, retrieved_dn2 = verify(SIGNED_MSG2, self.ca_dir, False)
        
        if not retrieved_dn2 == TEST_CERT_DN:
            print retrieved_dn2
            print TEST_CERT_DN
            self.fail("The DN of the verified message didn't match the cert.")
            
        if not retrieved_msg2.strip() == MSG2:
            print retrieved_msg2
            print MSG2
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
            
        # invalid cipher
        try:
            encrypted = encrypt(MSG, self.certpath, 'aes1024')
        except CryptoException:
            pass    
        
            
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
            self.fail('The self signed certificate should validate against'
                      'itself in a CA directory.')
            
        if verify_cert(TEST_CERT, '/tmp', False):
            self.fail("The verify method isn't checking the CA dir correctly.")
            
        if verify_cert('bloblo', self.ca_dir, False):
            self.fail('Nonsense successfully verified.')
 
        if verify_cert(TEST_CERT, self.ca_dir, True):
            self.fail('The self-signed certificate should not be verified ' +
                      'if CRLs are checked.')
        
        try:    
            if verify_cert(None, self.ca_dir, False):
                self.fail('Verified None rather than certificate string.')
        except CryptoException:
            pass

################################################################
# Test data below.
################################################################

TEST_CERT_DN = '/C=UK/O=STFC/OU=SC/CN=Test Cert'

TEST_CERT_FILE = '/tmp/test.crt'

TEST_KEY_FILE = '/tmp/test.key'

TEST_CA_DIR='/tmp'

MSG = 'This is some test data.'

# openssl smime -encrypt -in msg.text test.cert
ENCRYPTED_MSG = '''MIME-Version: 1.0
Content-Disposition: attachment; filename="smime.p7m"
Content-Type: application/x-pkcs7-mime; smime-type=enveloped-data; name="smime.p7m"
Content-Transfer-Encoding: base64

MIIBSAYJKoZIhvcNAQcDoIIBOTCCATUCAQAxgeQwgeECAQAwSjA9MQswCQYDVQQG
EwJVSzENMAsGA1UECgwEU1RGQzELMAkGA1UECwwCU0MxEjAQBgNVBAMMCVRlc3Qg
Q2VydAIJAO90ilCRmLiVMA0GCSqGSIb3DQEBAQUABIGAk1+nwYVXhLe8XmbksVo6
ZeQzdKMJV9pwP32eAiyncIPjm0GpyHpEvYaJ1+4+vDWyqA8MR912j0wVxTFKM3to
RynPyC98gykaUflI9pKKvo/Um3FDV6goH1kLmT+/1qEOXjDff9iZBmZ+AWNM9LBN
8kHoIMGymCqM8zZ6OUt3VIowSQYJKoZIhvcNAQcBMBoGCCqGSIb3DQMCMA4CAgCg
BAirHdYutwNXk4AgB87AFNZ43NSQtj++5QXfRoRpfsBbs7GFgfOVA+ULT5Y=
'''

# openssl smime -sign -signer test.cert -inkey test.key -in msg.text -text
SIGNED_MSG = '''MIME-Version: 1.0
Content-Type: multipart/signed; protocol="application/x-pkcs7-signature"; micalg="sha1"; boundary="----D23AB54130D33D70AF44A49F6A408898"

This is an S/MIME signed message

------D23AB54130D33D70AF44A49F6A408898
Content-Type: text/plain

This is some test data.

------D23AB54130D33D70AF44A49F6A408898
Content-Type: application/x-pkcs7-signature; name="smime.p7s"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="smime.p7s"

MIIETwYJKoZIhvcNAQcCoIIEQDCCBDwCAQExCzAJBgUrDgMCGgUAMAsGCSqGSIb3
DQEHAaCCAkwwggJIMIIBsaADAgECAgkA73SKUJGYuJUwDQYJKoZIhvcNAQEFBQAw
PTELMAkGA1UEBhMCVUsxDTALBgNVBAoMBFNURkMxCzAJBgNVBAsMAlNDMRIwEAYD
VQQDDAlUZXN0IENlcnQwHhcNMTUxMTI2MTYwNjM2WhcNMTYxMTI2MTYwNjM2WjA9
MQswCQYDVQQGEwJVSzENMAsGA1UECgwEU1RGQzELMAkGA1UECwwCU0MxEjAQBgNV
BAMMCVRlc3QgQ2VydDCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAwCpCTGZ5
c+IbjK17Pb1W/5eg8NfD168J9QsSqgx3yZ5oBuKLMBm5BPzMnngfTg+hvixKLJlG
tEeEZDSIlRzFOZGIUthk+JwDVXkYWZI8WYE+4dOLtWfuzKPFhdaYUdsrIRtVvc0i
iAx/kumvehINXpS6d7VDVlS9sVyUSOWEkPUCAwEAAaNQME4wHQYDVR0OBBYEFKSZ
/T/S12miawyp5maL0GTENilxMB8GA1UdIwQYMBaAFKSZ/T/S12miawyp5maL0GTE
NilxMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEFBQADgYEAVDWaM2axblp2cmYl
3w5lHSibl4wExsn440Vnrhlpsc586+Jg2N/d57DyrO8SWVvSivN4VkENSevPCtKo
Jb7dyszxlLUphg7XrJb9hcFUL5/mKV84x/0z/UTbD7aB9PDT8n0UwgbUCpB94P3v
x7tQnr4ggbcIoOD/w2mxeG3Dd7QxggHLMIIBxwIBATBKMD0xCzAJBgNVBAYTAlVL
MQ0wCwYDVQQKDARTVEZDMQswCQYDVQQLDAJTQzESMBAGA1UEAwwJVGVzdCBDZXJ0
AgkA73SKUJGYuJUwCQYFKw4DAhoFAKCB2DAYBgkqhkiG9w0BCQMxCwYJKoZIhvcN
AQcBMBwGCSqGSIb3DQEJBTEPFw0xNTExMjYxNjA5MTlaMCMGCSqGSIb3DQEJBDEW
BBS4mGqHlYCOu0+aUiwPuT3+Q8yGEDB5BgkqhkiG9w0BCQ8xbDBqMAsGCWCGSAFl
AwQBKjALBglghkgBZQMEARYwCwYJYIZIAWUDBAECMAoGCCqGSIb3DQMHMA4GCCqG
SIb3DQMCAgIAgDANBggqhkiG9w0DAgIBQDAHBgUrDgMCBzANBggqhkiG9w0DAgIB
KDANBgkqhkiG9w0BAQEFAASBgLXfxWyDPzKJ4zjozVMkzIHIIYC1NHCMQzIqFNmy
LCORY7Yd1DTsHv1Qshq0u/yA+6BWCN0S3MlUWJbnAN4zbyAH7EkgVZkymkn4KQyL
Si6AG6HNsYICeZW6gK/FW6ClKbXamygELe3Nx5cbfVEfT0Jsz2vj1gtS+tz87InJ
SqqH

------D23AB54130D33D70AF44A49F6A408898--'''

# Created same way as SIGNED_MSG but text manually converted to quoted-printable
# and Content-Type and Content-Transfer-Encoding fields added in manually.
SIGNED_MSG2 = '''MIME-Version: 1.0
Content-Type: multipart/signed; protocol="application/x-pkcs7-signature"; micalg="sha1"; boundary="----C4DE0669C598F78D53E9A61C6BB38924"

This is an S/MIME signed message

------C4DE0669C598F78D53E9A61C6BB38924
Content-Type: text/xml; charset=utf8
Content-Transfer-Encoding: quoted-printable

<com:UsageRecord xmlns:com=3D"http://eu-emi.eu/namespaces/2012/11/computere=
cord"><com:RecordIdentity com:recordId=3D"62991a08-909b-4516-aa30-3732ab3d8=
998" com:createTime=3D"2013-02-22T15:58:44.567+01:00"/><com:JobIdentity><co=
m:GlobalJobId>ac2b1157-7aff-42d9-945e-389aa9bbb19a</com:GlobalJobId><com:Lo=
calJobId>7005</com:LocalJobId></com:JobIdentity><com:UserIdentity><com:Glob=
alUserName com:type=3D"rfc2253">CN=3DBjoern Hagemeier,OU=3DForschungszentru=
m Juelich GmbH,O=3DGridGermany,C=3DDE</com:GlobalUserName><com:LocalUserId>=
bjoernh</com:LocalUserId><com:LocalGroup>users</com:LocalGroup></com:UserId=
entity><com:JobName>HiLA</com:JobName><com:Status>completed</com:Status><co=
m:ExitStatus>0</com:ExitStatus><com:Infrastructure com:type=3D"grid"/><com:=
Middleware com:name=3D"unicore">unicore</com:Middleware><com:WallDuration>P=
T0S</com:WallDuration><com:CpuDuration>PT0S</com:CpuDuration><com:ServiceLe=
vel com:type=3D"HEPSPEC">1.0</com:ServiceLevel><com:Memory com:metric=3D"to=
tal" com:storageUnit=3D"KB" com:type=3D"physical">0</com:Memory><com:Memory=
 com:metric=3D"total" com:storageUnit=3D"KB" com:type=3D"shared">0</com:Mem=
ory><com:TimeInstant com:type=3D"uxToBssSubmitTime">2013-02-22T15:58:44.568=
+01:00</com:TimeInstant><com:TimeInstant com:type=3D"uxStartTime">2013-02-2=
2T15:58:46.563+01:00</com:TimeInstant><com:TimeInstant com:type=3D"uxEndTim=
e">2013-02-22T15:58:49.978+01:00</com:TimeInstant><com:TimeInstant com:type=
=3D"etime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant com:=
type=3D"ctime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant =
com:type=3D"qtime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInst=
ant com:type=3D"maxWalltime">2013-02-22T16:58:45+01:00</com:TimeInstant><co=
m:NodeCount>1</com:NodeCount><com:Processors>2</com:Processors><com:EndTime=
>2013-02-22T15:58:45+01:00</com:EndTime><com:StartTime>2013-02-22T15:58:45+=
01:00</com:StartTime><com:MachineName>zam052v15.zam.kfa-juelich.de</com:Mac=
hineName><com:SubmitHost>zam052v02</com:SubmitHost><com:Queue com:descripti=
on=3D"execution">batch</com:Queue><com:Site>zam052v15.zam.kfa-juelich.de</c=
om:Site><com:Host com:primary=3D"false" com:description=3D"CPUS=3D2;SLOTS=
=3D1,0">zam052v15</com:Host></com:UsageRecord>

------C4DE0669C598F78D53E9A61C6BB38924
Content-Type: application/x-pkcs7-signature; name="smime.p7s"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="smime.p7s"

MIIETwYJKoZIhvcNAQcCoIIEQDCCBDwCAQExCzAJBgUrDgMCGgUAMAsGCSqGSIb3
DQEHAaCCAkwwggJIMIIBsaADAgECAgkA73SKUJGYuJUwDQYJKoZIhvcNAQEFBQAw
PTELMAkGA1UEBhMCVUsxDTALBgNVBAoMBFNURkMxCzAJBgNVBAsMAlNDMRIwEAYD
VQQDDAlUZXN0IENlcnQwHhcNMTUxMTI2MTYwNjM2WhcNMTYxMTI2MTYwNjM2WjA9
MQswCQYDVQQGEwJVSzENMAsGA1UECgwEU1RGQzELMAkGA1UECwwCU0MxEjAQBgNV
BAMMCVRlc3QgQ2VydDCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAwCpCTGZ5
c+IbjK17Pb1W/5eg8NfD168J9QsSqgx3yZ5oBuKLMBm5BPzMnngfTg+hvixKLJlG
tEeEZDSIlRzFOZGIUthk+JwDVXkYWZI8WYE+4dOLtWfuzKPFhdaYUdsrIRtVvc0i
iAx/kumvehINXpS6d7VDVlS9sVyUSOWEkPUCAwEAAaNQME4wHQYDVR0OBBYEFKSZ
/T/S12miawyp5maL0GTENilxMB8GA1UdIwQYMBaAFKSZ/T/S12miawyp5maL0GTE
NilxMAwGA1UdEwQFMAMBAf8wDQYJKoZIhvcNAQEFBQADgYEAVDWaM2axblp2cmYl
3w5lHSibl4wExsn440Vnrhlpsc586+Jg2N/d57DyrO8SWVvSivN4VkENSevPCtKo
Jb7dyszxlLUphg7XrJb9hcFUL5/mKV84x/0z/UTbD7aB9PDT8n0UwgbUCpB94P3v
x7tQnr4ggbcIoOD/w2mxeG3Dd7QxggHLMIIBxwIBATBKMD0xCzAJBgNVBAYTAlVL
MQ0wCwYDVQQKDARTVEZDMQswCQYDVQQLDAJTQzESMBAGA1UEAwwJVGVzdCBDZXJ0
AgkA73SKUJGYuJUwCQYFKw4DAhoFAKCB2DAYBgkqhkiG9w0BCQMxCwYJKoZIhvcN
AQcBMBwGCSqGSIb3DQEJBTEPFw0xNTExMjYxNjI0MTRaMCMGCSqGSIb3DQEJBDEW
BBSsAbgU5Xqg/QNNwbXFBxU/k7PFmzB5BgkqhkiG9w0BCQ8xbDBqMAsGCWCGSAFl
AwQBKjALBglghkgBZQMEARYwCwYJYIZIAWUDBAECMAoGCCqGSIb3DQMHMA4GCCqG
SIb3DQMCAgIAgDANBggqhkiG9w0DAgIBQDAHBgUrDgMCBzANBggqhkiG9w0DAgIB
KDANBgkqhkiG9w0BAQEFAASBgJ+Wn5Huc7Kyxw1yiHp1dbzVUpU1f4LWJiZLL3+c
+6jJAU1yGqI9awV1XrM7vcrw7Rqo9DQTGWBJ57VW02BAfYiNsKax2rIQmSj74L6a
2n4xYtDgTC27PBLqs7vX/9AzNx40MdWl61MTIXpJcgDAV0LzAyLZvE3ZlPZWrKz+
KH1d

------C4DE0669C598F78D53E9A61C6BB38924--'''

MSG2 = '''<com:UsageRecord xmlns:com="http://eu-emi.eu/namespaces/2012/11/computerecord"><com:RecordIdentity com:recordId="62991a08-909b-4516-aa30-3732ab3d8998" com:createTime="2013-02-22T15:58:44.567+01:00"/><com:JobIdentity><com:GlobalJobId>ac2b1157-7aff-42d9-945e-389aa9bbb19a</com:GlobalJobId><com:LocalJobId>7005</com:LocalJobId></com:JobIdentity><com:UserIdentity><com:GlobalUserName com:type="rfc2253">CN=Bjoern Hagemeier,OU=Forschungszentrum Juelich GmbH,O=GridGermany,C=DE</com:GlobalUserName><com:LocalUserId>bjoernh</com:LocalUserId><com:LocalGroup>users</com:LocalGroup></com:UserIdentity><com:JobName>HiLA</com:JobName><com:Status>completed</com:Status><com:ExitStatus>0</com:ExitStatus><com:Infrastructure com:type="grid"/><com:Middleware com:name="unicore">unicore</com:Middleware><com:WallDuration>PT0S</com:WallDuration><com:CpuDuration>PT0S</com:CpuDuration><com:ServiceLevel com:type="HEPSPEC">1.0</com:ServiceLevel><com:Memory com:metric="total" com:storageUnit="KB" com:type="physical">0</com:Memory><com:Memory com:metric="total" com:storageUnit="KB" com:type="shared">0</com:Memory><com:TimeInstant com:type="uxToBssSubmitTime">2013-02-22T15:58:44.568+01:00</com:TimeInstant><com:TimeInstant com:type="uxStartTime">2013-02-22T15:58:46.563+01:00</com:TimeInstant><com:TimeInstant com:type="uxEndTime">2013-02-22T15:58:49.978+01:00</com:TimeInstant><com:TimeInstant com:type="etime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant com:type="ctime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant com:type="qtime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant com:type="maxWalltime">2013-02-22T16:58:45+01:00</com:TimeInstant><com:NodeCount>1</com:NodeCount><com:Processors>2</com:Processors><com:EndTime>2013-02-22T15:58:45+01:00</com:EndTime><com:StartTime>2013-02-22T15:58:45+01:00</com:StartTime><com:MachineName>zam052v15.zam.kfa-juelich.de</com:MachineName><com:SubmitHost>zam052v02</com:SubmitHost><com:Queue com:description="execution">batch</com:Queue><com:Site>zam052v15.zam.kfa-juelich.de</com:Site><com:Host com:primary="false" com:description="CPUS=2;SLOTS=1,0">zam052v15</com:Host></com:UsageRecord>'''

if __name__ == '__main__':
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
