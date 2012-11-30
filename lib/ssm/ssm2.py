'''
   Copyright (C) 2012 STFC

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
   
   @author: Will Rogers
'''

from ssm import crypto, LOGGER_ID
from dirq.QueueSimple import QueueSimple
from dirq.queue import Queue

import stomp
# Exception changed name between stomppy versions
try:
    from stomp.exception import ConnectFailedException
except ImportError:
    from stomp.exception import ReconnectFailedException \
            as ConnectFailedException

import socket
import time
import logging

# Set up logging 
log = logging.getLogger(LOGGER_ID)

class Ssm2Exception(Exception):
    '''
    Exception for use by SSM2.
    '''
    pass

class Ssm2(object):
    '''
    Minimal SSM implementation.
    '''
    # Schema for the dirq message queue.
    QSCHEMA = {"body": "string", "signer":"string", "empaid":"string?"}
    CONNECTION_TIMEOUT = 10
    
    def __init__(self, hosts_and_ports, qpath, dest=None, listen=None, cert=None, key=None,
                 capath=None, use_ssl=False, username=None, password=None, enc_cert=None):
        '''
        Creates an SSM2 object.  If a listen value is supplied,
        this SSM2 will be a consumer.
        '''
        self._conn = None
        self._last_msg = None
            
        self._brokers = hosts_and_ports
        self._cert = cert
        self._key = key
        self._enc_cert = enc_cert
        self._capath = capath
        self._user = username
        self._pwd = password
        self._use_ssl = use_ssl
        # Use pwd if we're supplied user and pwd
        self._use_pwd = username is not None and password is not None
        self.connected = False
        
        self._listen = listen
        self._dest = dest
        
        self._valid_dns = []
        
        if dest is not None and listen is None:
            self._outq = QueueSimple(qpath)
        elif listen is not None:
            self._inq = Queue(qpath, schema=Ssm2.QSCHEMA)
        else:
            raise Ssm2Exception("Must be either producer or consumer.")
        
        if not crypto.check_cert_key(self._cert, self._key):
            raise Ssm2Exception("Cert and key don't match.")
        
    
    def set_dns(self, dn_list):
        '''
        Set the list of DNs which are allowed to sign incoming messages.
        '''
        self._valid_dns = dn_list
        
    ##########################################################################
    # Methods called by stomppy
    ##########################################################################
            
    def on_send(self, headers, unused_body):
        '''
        Called by stomppy when a message is sent.
        '''
        log.info("Sent message: " + headers['empa-id'])
        
    def on_message(self, headers, body):
        '''
        Called by stomppy when a message is received.
        
        Handle the message according to its content and headers.
        '''
        log.info("Received message: " + headers['empa-id'])
        raw_msg, signer = self._handle_msg(body)
        if raw_msg is None:
            log.info("Could not extract message; ignoring.")
        else:
            log.debug("Message content: %s" % raw_msg)
            self._inq.add({"body": raw_msg, 
                           "signer":signer, 
                           "empaid": headers['empa-id']})
        
    def on_error(self, unused_headers, body):
        '''
        Called by stomppy when an error frame is received.
        '''
        log.warn("Error message received: %s" % body)
        raise Ssm2Exception()
    
    def on_connected(self, unused_headers, unused_body):
        '''
        Called by stomppy when a connection is established.
        
        Track the connection.
        '''
        self.connected = True
        log.info("Connected.")
        
    def on_disconnected(self):
        '''
        Called by stomppy when disconnected from the broker.
        '''
        log.info("Disconnected from broker.")
        self.connected = False
        
    def on_receipt(self, headers, unused_body):
        '''
        Called by stomppy when the broker acknowledges receipt of a message.
        '''
        log.info("Broker received message: " + headers['receipt-id'])
        self._last_msg = headers['receipt-id']
        
    ##########################################################################
    # Message handling methods
    ##########################################################################
        
    def _handle_msg(self, text):
        '''
        Deal with the raw message contents appropriately:
        - decrypt if necessary
        - verify signature
        Return plain-text message and signer's DN.
        '''
        if not text.startswith("MIME-Version: 1.0"):
            raise Ssm2Exception("Not a valid message.")
        
        log.debug("Raw message contents: " + text)
        
        # encrypted
        if "application/pkcs7-mime"  or "application/x-pkcs7-mime" in text:
            try:
                text = crypto.decrypt(text, self._cert, self._key)
            except crypto.CryptoException, e:
                log.error("Failed to decrypt message: %s" % e)
                return None, None
        
        # always signed
        try:
            message, signer = crypto.verify(text, self._capath, False)
        except crypto.CryptoException, e:
            log.error("Failed to verify message: %s" % e)
            return None, None
        
        if signer not in self._valid_dns:
            log.error("Received message from invalid signer: %s" % signer)
        else:
            log.info("Valid signer: %s" % signer)
            
        return message, signer
        
    def _send_msg(self, message, msgid):
        '''
        Send one message using stomppy.  The message will be signed using 
        the host cert and key.  If an encryption certificate
        has been supplied, the message will also be encrypted.
        '''
        log.info("Sending message: " + msgid)
        headers = {'destination': self._dest, 'receipt': msgid,
                   'empa-id': msgid}
        
        to_send = crypto.sign(message, self._cert, self._key)
        
        if self._enc_cert is not None:
            to_send = crypto.encrypt(to_send, self._enc_cert)
        
        log.info("Ready to send: " + msgid)
        self._conn.send(to_send, headers=headers)
        log.info("Sent: " + msgid)
        
    def has_msgs(self):
        '''
        Return True if there are any messages in the outgoing queue.
        '''
        return self._outq.count() > 0
        
    def send_all(self):
        '''
        Send all the messages in the outgoing queue.
        '''
        log.info("Found %s messages." % self._outq.count())
        for msgid in self._outq:
            if not self._outq.lock(msgid):
                raise Ssm2Exception("Message queue was locked.")
            
            text = self._outq.get(msgid)
            self._send_msg(text, msgid)
            
            while self._last_msg is None:
                log.info("Waiting for broker to accept message.")
                time.sleep(0.5)
            
            self._last_msg = None
            self._outq.remove(msgid)
        
        
    ###############################################################################           
    # Connection handling methods
    ###############################################################################  
    
    def _initialise_connection(self, host, port):
        """
        Create the self._connection object with the appropriate properties,
        but don't try to start the connection.
        """
        self._conn = stomp.Connection([(host, port)], 
                                      use_ssl=self._use_ssl,
                                      user = self._user,
                                      passcode = self._pwd,
                                      ssl_key_file = self._key,
                                      ssl_cert_file = self._cert)
        
        # You can set this in the constructor but only for stomppy version 3.
        # This works for stomppy 3 but doesn't break stomppy 2.
        self._conn.__reconnect_attempts_max = 1
        self._conn.__timeout = Ssm2.CONNECTION_TIMEOUT
        
        self._conn.set_listener("SSM", self)
        
    def handle_connect(self):
        """
        Assuming that the SSM has retrieved the details of the broker or 
        brokers it wants to connect to, connect to one.
        
        If more than one is in the list self._network_brokers, try to 
        connect to each in turn until successful.
        """
        for host, port in self._brokers:
            self._initialise_connection(host, port)
            try:
                self.start_connection()
                break
            except ConnectFailedException, e:
                # ConnectFailedException doesn't provide a message.
                log.warn("Failed to connect to %s:%s." % (host, port))
            except Ssm2Exception, e:
                log.warn("Failed to connect to %s:%s: %s" % (host, port, str(e)))
                
        if not self.connected:
            raise Ssm2Exception("Attempts to start the SSM failed.  The system will exit.")

    def handle_disconnect(self):
        """
        When disconnected, attempt to reconnect using the same method as used
        when starting up.
        """
        self.connected = False
        # Shut down properly
        self.close_connection()
        
        # Sometimes the SSM will reconnect to the broker before it's properly 
        # shut down!  This prevents that.
        time.sleep(2)
        
        # Try again according to the same logic as the initial startup
        try:
            self.handle_connect()
        except Ssm2Exception:
            self.connected = False
            
        # If reconnection fails, admit defeat.
        if not self.connected:
            error_message = "Reconnection attempts failed and have been abandoned."
            raise Ssm2Exception(error_message)
        
    def start_connection(self):
        """
        Once self._connection exists, attempt to start it and subscribe
        to the relevant topics.
        
        If the timeout is reached without receiving confirmation of 
        connection, raise an exception.
        """
        if self._conn is None:
            raise Ssm2Exception("Called start_connection() before a \
                    connection object was initialised.")
            
        self._conn.start()
        self._conn.connect(wait = True)
        
        if self._dest is not None:
            log.info('Will send messages to: %s' % self._dest)
             
        if self._listen is not None:
            self._conn.subscribe(destination=self._listen, ack='auto')
            log.info("Subscribing to: %s" % self._listen)
            
        i = 0
        while not self.connected:
            time.sleep(0.1)
            if i > Ssm2.CONNECTION_TIMEOUT * 10:
                err = "Timed out while waiting for connection. "
                err += "Check the connection details."
                raise Ssm2Exception(err)
            i += 1
            
    def close_connection(self):
        """
        Close the connection.  This is important because it runs 
        in a separate thread, so it can outlive the main process 
        if it is not ended.
        """
        try:
            self._conn.disconnect()
        except (stomp.exception.NotConnectedException, socket.error):
            self._conn = None
        except AttributeError:
            # AttributeError if self._connection is None already
            pass
        
        log.info("SSM connection ended.")
