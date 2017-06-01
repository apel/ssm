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

    # Determine the type of SSM to configure (STOMP or REST (AMS))
    try:
        destination_type = cp.get('SSM Type', 'destination type')
        protocol = cp.get('SSM Type', 'protocol')

    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        # if newer configuration settings 'protocol' and 'destination type'
        # are not set, assume it's an old style STOMP BROKER for
        # backwards compatability.
        log.debug('No options supplied for destination_type and/or protocol.')
        destination_type = 'STOMP-BROKER'
        protocol = 'STOMP'

    log.info('Setting up SSM with Dest Type: %s, Protocol : %s'
             % (destination_type, protocol))

    # These variables are only set by one type of SSM
    # so set a sensible default here, possibly
    # to be overridden later
    # Set a default for STOMP only vars
    brokers = None
    use_ssl = None
    # Set a deafault fot AMS only vars
    token = None
    project = None
    topic = None
    # Shared vars are not set here, they must have
    # sensible defaults set in the config parsing

    if destination_type == 'STOMP-BROKER':
        # We are setting up an SSM to connect to an old style STOMP Broker
        # If we can't get a broker to connect to, we have to give up.
        try:
            bdii_url = cp.get('broker', 'bdii')
            log.info('Retrieving broker details from %s ...', bdii_url)
            bg = StompBrokerGetter(bdii_url)
            use_ssl = cp.getboolean('broker', 'use_ssl')
            if use_ssl:
                service = STOMP_SSL_SERVICE
            else:
                service = STOMP_SERVICE
            brokers = bg.get_broker_hosts_and_ports(service, cp.get('broker', 'network'))
            log.info('Found %s brokers.', len(brokers))

        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
            try:
                host = cp.get('broker', 'host')
                port = cp.get('broker', 'port')
                brokers = [(host, int(port))]
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
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

    else:
        # We are setting up an SSM to connect to a new stlye ARGO AMS
        try:
            token = cp.get('AMS', 'token')
            project = cp.get('AMS', 'project')
            topic = cp.get('AMS', 'topic')
        except (ConfigParser.Error, ValueError, IOError), err:

            log.error('Error configuring AMS values: %s' % str(err))
            log.error('SSM will exit.')
            print 'SSM failed to start.  See log file for details.'
            sys.exit(1)

    # Regardless of protocol, the SSM needs a destination
    try:
        destination = cp.get('messaging', 'destination')

    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
        log.error('No destination is configured.')
        log.error('SSM will exit.')
        print 'SSM failed to start.  See log file for details.'
        sys.exit(1)

    # Regardless of protocol, the SSM needs a path to read messages
    try:
        path = cp.get('messaging', 'path')

    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
        log.error('No message queue is configured.')
        log.error('SSM will exit.')
        print 'SSM failed to start.  See log file for details.'
        sys.exit(1)

    # Regardless of protocol, the SSM needs a certificate and a key
    # for the crypto verification    
    try:
        cert = cp.get('certificates', 'certificate')
        key = cp.get('certificates', 'key')

    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), error:
        log.error('No certificate or key set in conf file')
        log.error(error)
        log.error('SSM will exit')
        print 'SSM failed to start.  See log file for details.'
        sys.exit(1)

    # Regardless of protocol, the SSM might need a ca
    try:
        capath = cp.get('certificates', 'capath')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), error:
        log.warning('No capath set in cfg file.')

    server_cert = None
    verify_server_cert = True
    try:
        server_cert = cp.get('certificates', 'server_cert')
        try:
            verify_server_cert = cp.getboolean('certificates', 'verify_server_cert')
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            pass

    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        log.info('No server certificate supplied.  Will not encrypt messages.')

    try:
        sender = Ssm2(brokers, 
                      path,
                      cert,
                      key,
                      dest=destination,
                      use_ssl=use_ssl,
                      capath=capath,
                      enc_cert=server_cert,
                      verify_enc_cert=verify_server_cert,
                      dest_type=destination_type,
                      protocol=protocol,
                      project=project,
                      topic=topic,
                      password=token)

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
        log.error('Exception type: %s', e.__class__)

    try:
        sender.close_connection()
    except UnboundLocalError:
        # SSM not set up.
        pass

    log.info('SSM has shut down.')
    log.info(LOG_BREAK)
        
    
if __name__ == '__main__':
    main()
