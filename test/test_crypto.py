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
            self.fail('The self signed certificate should validate against \
            itself in a CA directory.')
            
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
