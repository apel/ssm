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
        
        ca_certs = [TEST_CERT, CERT2]

        self.ca_dir = tempfile.mkdtemp(prefix='ca')
        for cert in ca_certs:
            p1 = Popen(['openssl', 'x509', '-subject_hash', '-noout'],
                       stdin=PIPE, stdout=PIPE, stderr=PIPE)
            hash_name, unused_error = p1.communicate(cert)
            ca_certpath = os.path.join(self.ca_dir, hash_name.strip() + '.0')
            ca_cert = open(ca_certpath, 'w')
            ca_cert.write(cert)
            ca_cert.close()

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
            self.fail("The verified message didn't match the original.")
            
    def test_verify(self):
        
        retrieved_msg, retrieved_dn = verify(SIGNED_MSG, self.ca_dir, False)
        
        if not retrieved_dn == TEST_CERT_DN:
            self.fail("The DN of the verified message didn't match the cert.")
            
        if not retrieved_msg.strip() == MSG:
            self.fail("The verified messge didn't match the original.")
            
        retrieved_msg2, retrieved_dn2 = verify(SIGNED_MSG2, self.ca_dir, False)
        
        if not retrieved_dn2 == CERT2_DN:
            print retrieved_dn2
            print CERT2_DN
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

# openssl req -x509 -nodes -days 365 -subj '/C=UK/O=STFC/OU=SC/CN=adrian coveney' -newkey rsa:1024 -keyout test.key -out test.cert

TEST_CERT_DN = '/C=UK/O=STFC/OU=SC/CN=adrian coveney'

TEST_CERT = '''-----BEGIN CERTIFICATE-----
MIICUjCCAbugAwIBAgIJAOZv73BJdvtxMA0GCSqGSIb3DQEBBQUAMEIxCzAJBgNV
BAYTAlVLMQ0wCwYDVQQKDARTVEZDMQswCQYDVQQLDAJTQzEXMBUGA1UEAwwOYWRy
aWFuIGNvdmVuZXkwHhcNMTQxMDE2MDkxMDU4WhcNMTUxMDE2MDkxMDU4WjBCMQsw
CQYDVQQGEwJVSzENMAsGA1UECgwEU1RGQzELMAkGA1UECwwCU0MxFzAVBgNVBAMM
DmFkcmlhbiBjb3ZlbmV5MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCqa3Xu
OEVaEd4j6jQnvRLYCZ1fzKDQbsN6Meo1h8xbUrcEFJoN47kgclIw4KkqCnyiBUp+
fYHWlulx/f1WI2BD7PxslGpqb9YOsWqQhG2tW/s8AolDI4KthE9V7oA4N1ownl+J
ihfJrykBoK7N8ZiKQD1gcx+N1bbbI9Ev2AvuBwIDAQABo1AwTjAdBgNVHQ4EFgQU
3NWKbrFpY8j4xLUH7dFJYsP6P9wwHwYDVR0jBBgwFoAU3NWKbrFpY8j4xLUH7dFJ
YsP6P9wwDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQUFAAOBgQBCrLVWedMqqUWI
MDuiqKkAXD9Xb03SQKJKJQ2QyN+vP7s+wDXl0rLx5eEecvGwMrN+h8xo1M8mQruk
7kZrOEUCfTvKqbyeDQHxo8I/Sr52VGbEjKYgLgnIKEneshjK1RMxKgwQqbxE0miZ
MmEcxCQ0YEVqvq1CExWOYmKNMib3pg==
-----END CERTIFICATE-----'''

TEST_KEY = '''-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAKprde44RVoR3iPq
NCe9EtgJnV/MoNBuw3ox6jWHzFtStwQUmg3juSByUjDgqSoKfKIFSn59gdaW6XH9
/VYjYEPs/GyUampv1g6xapCEba1b+zwCiUMjgq2ET1XugDg3WjCeX4mKF8mvKQGg
rs3xmIpAPWBzH43Vttsj0S/YC+4HAgMBAAECgYBypQgY0dIV3Z9LGessMI3Ut+Me
51Hn5huqwJmGmWxooyRrolBgt6l6om2YZAppNdTSSizrGxOVgMBa5zreD75Z2q48
PU44RQVgvfwWBqEz8U/SeFBjVi6eTeQtKYimJmmLNhYm9uzaZEWfx3taDwSgMKEV
BTf6KoRX0otur2xbwQJBANOYr/fF3xhL6No2WLU7QjzMVmBr2PbPYrj03rgF+erJ
w0PU02hU7bcfrPQr0WpDyshpag0XQO/XARdd/1N521UCQQDOLrG4r5FQxW8rcNyb
dAp8ZD/AG02dViD1+3+6Fx2ONBHv7OIAA7MJpFHDoHmQrPdGBgFq7WhuCRaJS6a5
FzvrAkEAzl2y+Tbtf3fBUNkCKTbzQfKUJ5PnVccrZHHFqbqCZL+EhmpSCQYTla75
8mWt5zLY2h8dREkylvedY9nUA+jrxQJBAMOTu3Vq5LbvcTKNzlWPT1sLZQV/YLI8
PuvWcyQ8RQbdEZ663u4QlEYzHnQoxuebirtbewDIzmSCLmRx5GZySZ0CQHGdTWwf
2BUpz1Y7hkbt2yP7+UUtRnAWvMBm/1J/HGdjU+lPlUQgp7aDU48q7ZzdrGQBMKyI
GDG32bRsY7byBfE=
-----END PRIVATE KEY-----'''

# Certificate of the key which signed SIGNED_MSG2
CERT2 = '''
-----BEGIN CERTIFICATE-----
MIICXTCCAcagAwIBAgIEUSdrRzANBgkqhkiG9w0BAQUFADBzMSUwIwYDVQQDExx6
YW0wNTJ2MDUuemFtLmtmYS1qdWVsaWNoLmRlMScwJQYDVQQLEx5Gb3JzY2h1bmdz
emVudHJ1bSBKdWVsaWNoIEdtYkgxFDASBgNVBAoTC0dyaWRHZXJtYW55MQswCQYD
VQQGEwJERTAeFw0xMzAyMjIxMjU3NDNaFw0xMzA1MjMxMjU3NDNaMHMxJTAjBgNV
BAMTHHphbTA1MnYwNS56YW0ua2ZhLWp1ZWxpY2guZGUxJzAlBgNVBAsTHkZvcnNj
aHVuZ3N6ZW50cnVtIEp1ZWxpY2ggR21iSDEUMBIGA1UEChMLR3JpZEdlcm1hbnkx
CzAJBgNVBAYTAkRFMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCXa+Yiyot9
y7oX8yGPgoGtLOMX3QRq+JWYhdgiR49PIKb8yRDm3l2xZWKl2qLfUshNCCj5SfS5
EyL9/wRZdcbmKo8SHBy+kr6lkCTeIDUhhI3zwKqweliY8+7Kc/E7azxp9hzuvvWE
ogW184GXiLi+aVvVVepwP6bRnqnG6PUNmwIDAQABMA0GCSqGSIb3DQEBBQUAA4GB
AHY1RuOjuNjqsF/Azsn1ebVlm8qVVU0By4I6atZTsFLiOH76kbVva/WjpT0oAlRt
Qhw6AbzXUU1MAiO5tgQamYDmSsrqwPvXybnJM6p21iVgjRKuulmEbdeV+ccUxi7a
+Jb39KeuDQgo9RIvc/j6Qv+1LReBpgGqKLxZijVXd6Ci
-----END CERTIFICATE-----
'''

CERT2_DN = '/CN=zam052v05.zam.kfa-juelich.de/OU=Forschungszentrum Juelich GmbH/O=GridGermany/C=DE'

MSG = 'This is some test data.'

# openssl smime -encrypt -in msg.text test.cert
ENCRYPTED_MSG = '''MIME-Version: 1.0
Content-Disposition: attachment; filename="smime.p7m"
Content-Type: application/x-pkcs7-mime; smime-type=enveloped-data; name="smime.p7m"
Content-Transfer-Encoding: base64

MIIBTQYJKoZIhvcNAQcDoIIBPjCCAToCAQAxgekwgeYCAQAwTzBCMQswCQYDVQQG
EwJVSzENMAsGA1UECgwEU1RGQzELMAkGA1UECwwCU0MxFzAVBgNVBAMMDmFkcmlh
biBjb3ZlbmV5AgkA5m/vcEl2+3EwDQYJKoZIhvcNAQEBBQAEgYB9xvm+Nvpfu8zD
xIcV7BC0P6wpZYqy+DhW/10JN7Eq5Wsm4EZYRagbDSP2+WvNQ+tffLtmlH1lsFFe
3OViEBZOwSh3pXL6sFteftrZJJDaLnRh0mDjOZ6A/JhBZDbK/hzfyfrI3VSnJkY2
cC8GjWTaU7MASixEqTQC8AoP8NFW+DBJBgkqhkiG9w0BBwEwGgYIKoZIhvcNAwIw
DgICAKAECCntgjVbfq2WgCDZLJYHU7+qvZ0tcqx8dQkRaHJj7v99RUGX2PuaIglQ
2g==
'''

SIGNED_MSG = '''MIME-Version: 1.0
Content-Type: multipart/signed; protocol="application/x-pkcs7-signature"; micalg="sha1"; boundary="----75C746878BE47CBCE9CC86039A11C0DA"

This is an S/MIME signed message

------75C746878BE47CBCE9CC86039A11C0DA
This is some test data.

------75C746878BE47CBCE9CC86039A11C0DA
Content-Type: application/x-pkcs7-signature; name="smime.p7s"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="smime.p7s"

MIIEXgYJKoZIhvcNAQcCoIIETzCCBEsCAQExCzAJBgUrDgMCGgUAMAsGCSqGSIb3
DQEHAaCCAlYwggJSMIIBu6ADAgECAgkA5m/vcEl2+3EwDQYJKoZIhvcNAQEFBQAw
QjELMAkGA1UEBhMCVUsxDTALBgNVBAoMBFNURkMxCzAJBgNVBAsMAlNDMRcwFQYD
VQQDDA5hZHJpYW4gY292ZW5leTAeFw0xNDEwMTYwOTEwNThaFw0xNTEwMTYwOTEw
NThaMEIxCzAJBgNVBAYTAlVLMQ0wCwYDVQQKDARTVEZDMQswCQYDVQQLDAJTQzEX
MBUGA1UEAwwOYWRyaWFuIGNvdmVuZXkwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJ
AoGBAKprde44RVoR3iPqNCe9EtgJnV/MoNBuw3ox6jWHzFtStwQUmg3juSByUjDg
qSoKfKIFSn59gdaW6XH9/VYjYEPs/GyUampv1g6xapCEba1b+zwCiUMjgq2ET1Xu
gDg3WjCeX4mKF8mvKQGgrs3xmIpAPWBzH43Vttsj0S/YC+4HAgMBAAGjUDBOMB0G
A1UdDgQWBBTc1YpusWljyPjEtQft0Uliw/o/3DAfBgNVHSMEGDAWgBTc1YpusWlj
yPjEtQft0Uliw/o/3DAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBBQUAA4GBAEKs
tVZ50yqpRYgwO6KoqQBcP1dvTdJAokolDZDI368/uz7ANeXSsvHl4R5y8bAys36H
zGjUzyZCu6TuRms4RQJ9O8qpvJ4NAfGjwj9KvnZUZsSMpiAuCcgoSd6yGMrVEzEq
DBCpvETSaJkyYRzEJDRgRWq+rUITFY5iYo0yJvemMYIB0DCCAcwCAQEwTzBCMQsw
CQYDVQQGEwJVSzENMAsGA1UECgwEU1RGQzELMAkGA1UECwwCU0MxFzAVBgNVBAMM
DmFkcmlhbiBjb3ZlbmV5AgkA5m/vcEl2+3EwCQYFKw4DAhoFAKCB2DAYBgkqhkiG
9w0BCQMxCwYJKoZIhvcNAQcBMBwGCSqGSIb3DQEJBTEPFw0xNDEwMTYwOTQyMDVa
MCMGCSqGSIb3DQEJBDEWBBTZ9n+NhKrYFSBH6w0K4+tpPDS5FjB5BgkqhkiG9w0B
CQ8xbDBqMAsGCWCGSAFlAwQBKjALBglghkgBZQMEARYwCwYJYIZIAWUDBAECMAoG
CCqGSIb3DQMHMA4GCCqGSIb3DQMCAgIAgDANBggqhkiG9w0DAgIBQDAHBgUrDgMC
BzANBggqhkiG9w0DAgIBKDANBgkqhkiG9w0BAQEFAASBgCVDmnx8NHnx2CnthO32
nh2pWdbpITqVms0vQj8D090VZ+58wh4fV3Vj4SlPEuJ6+SG3ykyFsSkwfNQuQoib
F9hcuy4ZnFhbLzNBNR0EJmxybkirS0Q5iQv4SgAkfFIEgedsMWtAS904/hr/BCIH
UABUQKW4IyhAVpixFN94YQ7e

------75C746878BE47CBCE9CC86039A11C0DA--'''

SIGNED_MSG2 = '''Message-ID: <471108564.1391361545139805.JavaMail.root@zam052v05>
MIME-Version: 1.0
Content-Type: multipart/signed; protocol="application/pkcs7-signature"; micalg=sha1;
        boundary="----=_Part_69_779671724.1361545139802"

------=_Part_69_779671724.1361545139802
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
------=_Part_69_779671724.1361545139802
Content-Type: application/pkcs7-signature; name=smime.p7s; smime-type=signed-data
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="smime.p7s"
Content-Description: S/MIME Cryptographic Signature

MIAGCSqGSIb3DQEHAqCAMIACAQExCzAJBgUrDgMCGgUAMIAGCSqGSIb3DQEHAQAAoIAwggJdMIIB
xqADAgECAgRRJ2tHMA0GCSqGSIb3DQEBBQUAMHMxJTAjBgNVBAMTHHphbTA1MnYwNS56YW0ua2Zh
LWp1ZWxpY2guZGUxJzAlBgNVBAsTHkZvcnNjaHVuZ3N6ZW50cnVtIEp1ZWxpY2ggR21iSDEUMBIG
A1UEChMLR3JpZEdlcm1hbnkxCzAJBgNVBAYTAkRFMB4XDTEzMDIyMjEyNTc0M1oXDTEzMDUyMzEy
NTc0M1owczElMCMGA1UEAxMcemFtMDUydjA1LnphbS5rZmEtanVlbGljaC5kZTEnMCUGA1UECxMe
Rm9yc2NodW5nc3plbnRydW0gSnVlbGljaCBHbWJIMRQwEgYDVQQKEwtHcmlkR2VybWFueTELMAkG
A1UEBhMCREUwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAJdr5iLKi33LuhfzIY+Cga0s4xfd
BGr4lZiF2CJHj08gpvzJEObeXbFlYqXaot9SyE0IKPlJ9LkTIv3/BFl1xuYqjxIcHL6SvqWQJN4g
NSGEjfPAqrB6WJjz7spz8TtrPGn2HO6+9YSiBbXzgZeIuL5pW9VV6nA/ptGeqcbo9Q2bAgMBAAEw
DQYJKoZIhvcNAQEFBQADgYEAdjVG46O42OqwX8DOyfV5tWWbypVVTQHLgjpq1lOwUuI4fvqRtW9r
9aOlPSgCVG1CHDoBvNdRTUwCI7m2BBqZgOZKyurA+9fJuckzqnbWJWCNEq66WYRt15X5xxTGLtr4
lvf0p64NCCj1Ei9z+PpC/7UtF4GmAaoovFmKNVd3oKIAADGCAYAwggF8AgEBMHswczElMCMGA1UE
AxMcemFtMDUydjA1LnphbS5rZmEtanVlbGljaC5kZTEnMCUGA1UECxMeRm9yc2NodW5nc3plbnRy
dW0gSnVlbGljaCBHbWJIMRQwEgYDVQQKEwtHcmlkR2VybWFueTELMAkGA1UEBhMCREUCBFEna0cw
CQYFKw4DAhoFAKBdMBgGCSqGSIb3DQEJAzELBgkqhkiG9w0BBwEwHAYJKoZIhvcNAQkFMQ8XDTEz
MDIyMjE0NTg1OVowIwYJKoZIhvcNAQkEMRYEFM+ahH3DuE3LLQY78kZCtYbnE45vMA0GCSqGSIb3
DQEBAQUABIGAKhxtlcEaarnw1pbSlGmvKf5bI7n/WaXnYgkptOvoy75r6ZuhQHOOf3ffehpL9hMc
S6+br3IZPVEBr8kuhg6EpBNXuhZ3dE+PUF8P9qRDonHc1YuEvrng8svyZN+HpZl5S3XbbL0+4Rwf
hOcYKM8R3tVUpyuTNzskZnJmsrA7dvQAAAAAAAA=
------=_Part_69_779671724.1361545139802--
'''

MSG2 = '''<com:UsageRecord xmlns:com="http://eu-emi.eu/namespaces/2012/11/computerecord"><com:RecordIdentity com:recordId="62991a08-909b-4516-aa30-3732ab3d8998" com:createTime="2013-02-22T15:58:44.567+01:00"/><com:JobIdentity><com:GlobalJobId>ac2b1157-7aff-42d9-945e-389aa9bbb19a</com:GlobalJobId><com:LocalJobId>7005</com:LocalJobId></com:JobIdentity><com:UserIdentity><com:GlobalUserName com:type="rfc2253">CN=Bjoern Hagemeier,OU=Forschungszentrum Juelich GmbH,O=GridGermany,C=DE</com:GlobalUserName><com:LocalUserId>bjoernh</com:LocalUserId><com:LocalGroup>users</com:LocalGroup></com:UserIdentity><com:JobName>HiLA</com:JobName><com:Status>completed</com:Status><com:ExitStatus>0</com:ExitStatus><com:Infrastructure com:type="grid"/><com:Middleware com:name="unicore">unicore</com:Middleware><com:WallDuration>PT0S</com:WallDuration><com:CpuDuration>PT0S</com:CpuDuration><com:ServiceLevel com:type="HEPSPEC">1.0</com:ServiceLevel><com:Memory com:metric="total" com:storageUnit="KB" com:type="physical">0</com:Memory><com:Memory com:metric="total" com:storageUnit="KB" com:type="shared">0</com:Memory><com:TimeInstant com:type="uxToBssSubmitTime">2013-02-22T15:58:44.568+01:00</com:TimeInstant><com:TimeInstant com:type="uxStartTime">2013-02-22T15:58:46.563+01:00</com:TimeInstant><com:TimeInstant com:type="uxEndTime">2013-02-22T15:58:49.978+01:00</com:TimeInstant><com:TimeInstant com:type="etime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant com:type="ctime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant com:type="qtime">2013-02-22T15:58:44+01:00</com:TimeInstant><com:TimeInstant com:type="maxWalltime">2013-02-22T16:58:45+01:00</com:TimeInstant><com:NodeCount>1</com:NodeCount><com:Processors>2</com:Processors><com:EndTime>2013-02-22T15:58:45+01:00</com:EndTime><com:StartTime>2013-02-22T15:58:45+01:00</com:StartTime><com:MachineName>zam052v15.zam.kfa-juelich.de</com:MachineName><com:SubmitHost>zam052v02</com:SubmitHost><com:Queue com:description="execution">batch</com:Queue><com:Site>zam052v15.zam.kfa-juelich.de</com:Site><com:Host com:primary="false" com:description="CPUS=2;SLOTS=1,0">zam052v15</com:Host></com:UsageRecord>'''

if __name__ == '__main__':
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
