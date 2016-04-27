#!/usr/bin/env python

#   Copyright (C) 2012 STFC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

'''
Script to run a sending SSM.
@author: Will Rogers
'''

from ssm import __version__, set_up_logging, LOG_BREAK
from ssm.ssm2 import Ssm2, Ssm2Exception
from ssm.crypto import CryptoException
from ssm.brokers import StompBrokerGetter, STOMP_SERVICE, STOMP_SSL_SERVICE

import logging.config
import ldap
import sys
import os
from optparse import OptionParser
import ConfigParser


def main():
    '''
    Set up connection, send all messages and quit.
    '''
    ver = "SSM %s.%s.%s" % __version__
    op = OptionParser(description=__doc__, version=ver)
    op.add_option('-c', '--config', help='location of config file', 
                          default='/etc/apel/sender.cfg')
    op.add_option('-l', '--log_config', 
                        help='location of logging config file (optional)', 
                        default='/etc/apel/logging.cfg')
    (options, unused_args) = op.parse_args()
    
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
    
    log = logging.getLogger('ssmsend')
    
    log.info(LOG_BREAK)
    log.info('Starting sending SSM version %s.%s.%s.', *__version__)

    try:
        protocol = cp.get('messaging', 'protocol')
        if protocol == '':
            protocol = False
    except ConfigParser.NoOptionError, e:
        protocol = False

    if protocol == "STOMP":
        # If we can't get a broker to connect to, we have to give up.
        try:
            bdii_url = cp.get('broker','bdii')
            log.info('Retrieving broker details from %s ...', bdii_url)
            bg = StompBrokerGetter(bdii_url)
            use_ssl = cp.getboolean('broker', 'use_ssl')
            if use_ssl:
                service = STOMP_SSL_SERVICE
            else:
                service = STOMP_SERVICE
            brokers = bg.get_broker_hosts_and_ports(service, cp.get('broker','network'))
            log.info('Found %s brokers.', len(brokers))
        except ConfigParser.NoOptionError, e:
            try:
                host = cp.get('broker', 'host')
                port = cp.get('broker', 'port')
                brokers = [(host, int(port))]
            except ConfigParser.NoOptionError:
                log.error('Options incorrectly supplied for either single broker or \
                           broker network.  Please check configuration')
                log.error('System will exit.')
                log.info(LOG_BREAK)
                print 'SSM failed to start.  See log file for details.'
                sys.exit(1)
        except ldap.LDAPError, e:
            log.error('Could not connect to LDAP server: %s', e)
            log.error('System will exit.')
            log.info(LOG_BREAK)
            print 'SSM failed to start.  See log file for details.'
            sys.exit(1)
        
        if len(brokers) == 0:
            log.error('No brokers available.')
            log.error('System will exit.')
            log.info(LOG_BREAK)
            sys.exit(1)

    elif protocol == "REST":
        brokers = None     

    else:
       log.error('Unsupported protocol defined: %s' % protocol)
       print 'SSM failed to start.  See log file for details.'
       sys.exit(1)   

    try:
        server_cert = None
        verify_server_cert = True
        try:
            server_cert = cp.get('certificates','server_cert')
            try:
                verify_server_cert = cp.getboolean('certificates', 'verify_server_cert')
            except ConfigParser.NoOptionError:
                pass
        except ConfigParser.NoOptionError:
            log.info('No server certificate supplied.  Will not encrypt messages.')
            
        try:
            destination = cp.get('messaging', 'destination')
            if destination == '':
                raise Ssm2Exception('No destination queue is configured.')
        except ConfigParser.NoOptionError, e:
            raise Ssm2Exception(e)

        sender = Ssm2(brokers, 
                   cp.get('messaging','path'),
                   cert=cp.get('certificates','certificate'),
                   key=cp.get('certificates','key'),
                   dest=cp.get('messaging','destination'),
                   use_ssl=cp.getboolean('broker','use_ssl'),
                   capath=cp.get('certificates', 'capath'),
                   enc_cert=server_cert,
                   verify_enc_cert=verify_server_cert,
                   protocol=protocol)
        
        if sender.has_msgs():
            sender.handle_connect()
            sender.send_all()
            log.info('SSM run has finished.')
        else:
            log.info('No messages found to send.')
        
    except (Ssm2Exception, CryptoException), e:
        print 'SSM failed to complete successfully.  See log file for details.'
        log.error('SSM failed to complete successfully: %s', e)
    except Exception, e:
        print 'SSM failed to complete successfully.  See log file for details.'
        log.error('Unexpected exception in SSM: %s', e)
        log.exception('Exception type: %s', e.__class__)

    try:
        sender.close_connection()
    except UnboundLocalError:
        # SSM not set up.
        pass

    log.info('SSM has shut down.')
    log.info(LOG_BREAK)
        
    
if __name__ == '__main__':
    main()
