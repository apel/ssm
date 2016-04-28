'''
Created on 7 Dec 2011

@author: will
'''

from dirq.QueueSimple import QueueSimple
from mock import MagicMock

import ssm.ssm2

import os
import unittest
import shutil
import tempfile


class TestSsm(unittest.TestCase):
    '''
    Class used for testing SSM.
    '''

    def setUp(self):
        '''
        Set up a test SSM, and a test directory containing certificates.
        '''
        self._tmp_dir = tempfile.mkdtemp(prefix='ssm')

        self.cert_file, self.cert_path = tempfile.mkstemp(prefix='cert', dir=self._tmp_dir)
        os.write(self.cert_file, TEST_CERT)
        os.close(self.cert_file)


        self.key_file, self.key_path = tempfile.mkstemp(prefix='key', dir=self._tmp_dir)
        os.write(self.key_file, TEST_KEY)
        os.close(self.key_file)

        self._valid_dn = '/test/dn'
        self.valid_dn_file, self.valid_dn_path = tempfile.mkstemp(prefix='valid', dir=self._tmp_dir)
        os.write(self.valid_dn_file, self._valid_dn)
        os.close(self.valid_dn_file)

        self._cert_string = TEST_CERT
        self._key = TEST_KEY

        hosts_and_ports = [('not.a.broker', 123)]
        capath = '/not/a/path'
        certificate = self.cert_path
        key = self.key_path
        check_crls = False
        pidfile = self._tmp_dir + '/pidfile'

        listen = '/topic/test'

        dest = '/topic/test'

        self._msgdir = tempfile.mkdtemp(prefix='msgq')

        self._ssm = ssm.ssm2.Ssm2(hosts_and_ports, self._msgdir, certificate, key,
                                  dest=dest, listen=listen)

    def tearDown(self):
        '''Remove test directory and all contents.'''
        try:
            shutil.rmtree(self._msgdir)
            shutil.rmtree(self._tmp_dir)
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

    def test_send_via_rest(self):
        '''
        Test the SSM with REST protocol enabled.
        '''
        # re define some elements of the SSM to use REST
        # set SSM to use REST
        self._ssm._protocol = "REST"
        # set up a queue
        self._ssm._outq = QueueSimple('/var/spool/apel/outgoing')
        # mock the send message
        self._ssm._send_msg_rest = MagicMock()

        # add test message to queue
        self._ssm._outq.add(TEST_MESSAGE)
        # send message
        self._ssm.send_all()

        self.assertEqual(self._ssm._send_msg_rest.call_count, 1)

TEST_CERT = '''-----BEGIN CERTIFICATE-----
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
-----END CERTIFICATE-----'''
            
TEST_KEY = '''-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----'''

TEST_MESSAGE = '''APEL-cloud-message: v0.2
VMUUID: exampleVM1 2013-02-25 17:37:27+00:00
SiteName: exampleSite1
MachineName: one-2421
LocalUserId: 19
LocalGroupId: 101
GlobalUserName: NULL
FQAN: NULL
Status: completed
StartTime: 1361813847
EndTime: 1361813870
SuspendDuration: NULL
WallDuration: NULL
CpuDuration: NULL
CpuCount: 1
NetworkType: NULL
NetworkInbound: 0
NetworkOutbound: 0
Memory: 1000
Disk: NULL
StorageRecordId: NULL
ImageId: NULL
CloudType: OpenNebula
%%'''

if __name__ == '__main__':
    #import sys;sys.argv = ['', 'Test.test_get_a_broker']
    unittest.main()
