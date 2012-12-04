#!/usr/bin/env python
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

import logging.config
import sys
import os
from optparse import OptionParser
import ConfigParser

from ssm import __version__, set_up_logging
from ssm.ssm2 import Ssm2, Ssm2Exception
from ssm.crypto import CryptoException
from ssm.brokers import StompBrokerGetter, STOMP_SERVICE

def main():
    '''
    Set up connection, send all messages and quit.
    '''
    op = OptionParser(description=__doc__, version=__version__)
    op.add_option('-c', '--config', help='the location of config file', 
                          default='/etc/apel/sender.cfg')
    op.add_option('-l', '--log_config', help='location of the log config file', 
                          default='/etc/apel/logging.cfg')
    (options,_) = op.parse_args()
    
    
    cp = ConfigParser.ConfigParser()
    cp.read(options.config)
    
    # set up logging
    try:
        if os.path.exists(options.log_config):
            logging.config.fileConfig(options.log_config)
        else:
            set_up_logging(cp.get('logging', 'logfile'), 
                           cp.get('logging', 'level'),
                           cp.getboolean('logging', 'console'))
    except (ConfigParser.Error, ValueError, IOError), err:
        print 'Error configuring logging: %s' % str(err)
        print 'The system will exit.'
        sys.exit(1)
    
    log = logging.getLogger("ssmsend")
    
    log.info('========================================')
    log.info('Starting sending SSM version %s.%s.%s.' % __version__)
    # If we can't get a broker to connect to, we have to give up.
    try:
        bg = StompBrokerGetter(cp.get('broker','bdii'))
        brokers = bg.get_broker_hosts_and_ports(STOMP_SERVICE, cp.get('broker','network'))
    except ConfigParser.NoOptionError, e:
        try:
            host = cp.get('broker', 'host')
            port = cp.get('broker', 'port')
            brokers = [(host, int(port))]
        except ConfigParser.NoOptionError:
            log.error('Options incorrectly supplied for either single broker or broker network.  Please check configuration')
            log.error('System will exit.')
            log.info('========================================')
            print 'SSM failed to start.  See log file for details.'
            sys.exit(1)
    except ldap.SERVER_DOWN, e:
        log.error('Could not connect to LDAP server: %s' % e)
        log.error('System will exit.')
        log.info('========================================')
        print 'SSM failed to start.  See log file for details.'
        sys.exit(1)
        
    try:
        server_cert = cp.get('certificates','server')
    except ConfigParser.NoOptionError:
        log.info('No server certificate supplied.  Will not encrypt messages.')
        server_cert = None
    
    try:
        sender = Ssm2(brokers, 
                   cp.get('messaging','path'),
                   dest=cp.get('messaging','destination'),
                   cert=cp.get('certificates','certificate'),
                   key=cp.get('certificates','key'),
                   capath=cp.get('certificates', 'capath'),
                   enc_cert=server_cert)
        
        if sender.has_msgs():
            sender.handle_connect()
            sender.send_all()
            log.info('SSM run has finished.')
        else:
            log.info('No messages found to send.')
        
    except (Ssm2Exception, CryptoException), e:
        print 'SSM failed to complete successfully.  See log file for details.'
        log.error('SSM failed to complete successfully: %s' % e)
    except Exception, e:
        print 'SSM failed to complete successfully.  See log file for details.'
        log.error('Unexpected exception in SSM: %s, %s' % (type(e), e))
        log.error('Exception type: %s' % type(e))
        
    try:
        sender.close_connection()
    except UnboundLocalError:
        # SSM not set up.
        pass

    log.info('SSM has shut down.')
    log.info('========================================')
        
    
if __name__ == '__main__':
    main()
