'''
Created on 7 Dec 2011

@author: will
'''

import ssm
    
from message_db import MessageDB
 
import os
import unittest
import shutil
import tempfile

class TestSsm(unittest.TestCase):
    
    def setUp(self):
        """
        Set up a test SSM, and a test directory containing certificates.
        """
        
        self._tmp_dir = tempfile.mkdtemp(prefix="ssm")
        
        self.cert_file, self.cert_path = tempfile.mkstemp(prefix='cert', dir=self._tmp_dir)
        os.write(self.cert_file, TEST_CERT)
        os.close(self.cert_file)
        
        
        self.key_file, self.key_path = tempfile.mkstemp(prefix='key', dir=self._tmp_dir)
        os.write(self.key_file, TEST_KEY)
        os.close(self.key_file)
        
        self._valid_dn = "/test/dn"
        self.valid_dn_file, self.valid_dn_path = tempfile.mkstemp(prefix='valid', dir=self._tmp_dir)
        os.write(self.valid_dn_file, self._valid_dn)
        os.close(self.valid_dn_file)
        
        self._cert_string = TEST_CERT
        self._key = TEST_KEY
        
        c = ssm.Config() 
        c.bdii = "not a url"
        c.broker_network = "NETWORK"
        c.host = "not a broker"
        c.port = 123
        c.use_ssl = False
        c.capath = "/not/a/path"
        c.certificate = self.cert_path
        c.key = self.key_path
        c.check_crls = False
        c.daemon = True
        c.pidfile = self._tmp_dir + "/pidfile"
        
        cc = ssm.ConsumerConfig()
        cc.listen_to = "/topic/test"
        cc.valid_dn = self.valid_dn_path
        cc.read_valid_dn_interval = 60
        
        pc = ssm.ProducerConfig()
        pc.msg_check_time = 10
        
        pc.consumerDN = "/not/a/DN"
        pc.send_to = "/topic/test"
        pc.ack_queue = "/queue/ack"
        
        self._mdbdir =  tempfile.mkdtemp(prefix="mdb")
        mdb = MessageDB(self._mdbdir, True)
        
        self._ssm = ssm.SecureStompMessenger(mdb, c, pc, cc)


    def tearDown(self):
        """Remove test directory and all contents."""
        try:
            shutil.rmtree(self._mdbdir)
            shutil.rmtree(self._tmp_dir)
        except OSError, e:
            print "Error removing temporary directory %s" % self._tmp_dir
            print e
        
    def test_create_pidfile(self):
        
        # Inside the temporary directory, so will be removed by tearDown()
        self._ssm._create_pidfile()
        
        pidfile = self._ssm._configuration.pidfile
        
        f = open(pidfile)
        contents = f.readlines()
        if not len(contents) == 1:
            self.fail("There should be only one line in the pidfile.")
        if not (int(contents[0]) == os.getpid()):
            self.fail("The content of the pidfile should be the PID.")
    
    def test_remove_pidfile(self):
        """Manually create a file and check that it gets removed."""
        try:
            f = open(self._ssm._configuration.pidfile, 'w')
            f.write("This is not a pid.")
            f.close()
        except IOError:
            self.fail("Failed to create a file in the pidfile location.")
            
        if not os.path.exists(self._ssm._configuration.pidfile):
            self.fail("Failed to create a file in the pidfile location.")
        
        self._ssm._remove_pidfile()
        
        if os.path.exists(self._ssm._configuration.pidfile):
            self.fail("Failed to remove the file in the pidfile location.")
        
        
    def test_valid_sender(self):
        """
        Read DNs from the temporary file, and check that there is the 
        expected content.
        """
        self._ssm._read_valid_dns()
        
        if self._ssm._valid_sender("garbage"):
            self.fail("Accepted an invalid sender.")

        if not self._ssm._valid_sender(self._valid_dn):
            self.fail("Didn't recognise the one sender in the file.")
            
    def test_on_message(self):
        """
        This is quite a complicated method, so it would take a long time
        to write a comprehensive test.  Instead, I will start with where there
        might be problems.
        """
        
        # SSM crashed when headers were missing.  It should just ignore the
        # message.
        self._ssm.on_message({}, "")
  

        self._ssm.on_message({ssm.SSM_MSG_TYPE: ssm.SSM_NORMAL_MSG}, "")


    def test_check_ssm_config(self):
        """
        This test is incomplete, and will need a bit of thinking.
        """
        c = ssm.Config()
        try: 
            ssm.check_ssm_config(c, None, None)
            self.fail("Both producer and consumer configs can't be None")
        except ssm.SsmException:
            pass
        
        cc = ssm.ConsumerConfig()
        pc = ssm.ProducerConfig()
        c.daemon = False
        
        try: 
            ssm.check_ssm_config(c, cc, pc)
            self.fail("If there's a consumer config, c.daemon must be True")
        except ssm.SsmException:
            pass
        
            
    def test_fetch_brokers(self):
        '''
        Requires an internet connection to get information from the BDII.
        Could fail if the BDII is down. This isn't very unit-test-like.
        '''
        bdii = "ldap://lcg-bdii.cern.ch:2170"
        network = "PROD"
        brokers = ssm.fetch_brokers(bdii, network, False)
        
        if len(brokers) < 1:
            self.fail("No brokers found in the BDII.")
        
        host, port = brokers[0]
        if not str(port).isdigit():
            self.fail("Got a non-integer port from fetch_brokers()")
            
        if not '.' in host:
            self.fail("Didn't get a hostname from fetch_brokers()")
            
        
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
            
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_get_a_broker']
    unittest.main()