#!/usr/bin/env python

#   Copyright (C) 2012 STFC.
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
Script to run a receiving SSM.
@author: Will Rogers
'''

from ssm.brokers import StompBrokerGetter, STOMP_SERVICE, STOMP_SSL_SERVICE
from ssm.ssm2 import Ssm2, Ssm2Exception
from ssm import __version__, set_up_logging, LOG_BREAK

from stomp.exception import NotConnectedException

import time
import logging.config
import ldap
import os
import sys
from optparse import OptionParser 
from daemon import DaemonContext
import ConfigParser

# How often (in seconds) to read the list of valid DNs.
REFRESH_DNS = 600
log = None

def get_dns(dn_file):
    '''
    Retrieve a list of DNs from a file.
    '''
    dns = []
    f = None
    try:
        f = open(dn_file, 'r')
        lines = f.readlines()
        for line in lines:
            if line.isspace() or line.strip().startswith('#'):
                continue
            elif line.strip().startswith('/'):
                dns.append(line.strip())
            else:
                log.warn('DN in incorrect format: %s', line)
    finally:
        if f is not None:
            f.close()
    # If no valid DNs, SSM cannot receive any messages.
    if len(dns) == 0:
        raise Ssm2Exception('No valid DNs found in %s.  SSM will not start' % dn_file)

    log.debug('%s DNs found.', len(dns))
    return dns


def main():
    '''
    Set up connection, and listen for messages.
    '''
    ver = "SSM %s.%s.%s" % __version__
    op = OptionParser(description=__doc__, version=ver)
    op.add_option('-c', '--config', help='location of config file', 
                  default='/etc/apel/receiver.cfg')
    op.add_option('-l', '--log_config', 
                  help='location of logging config file (optional)', 
                  default='/etc/apel/logging.cfg')
    op.add_option('-d', '--dn_file', 
                  help='location of the file containing valid DNs', 
                  default='/etc/apel/dns')
    
    (options, unused_args) = op.parse_args()
        
    cp = ConfigParser.ConfigParser()
    cp.read(options.config)

    # These variables are only set by one type of SSM
    # so set a sensible default here, possibly
    # to be overridden later
    # Set a default for STOMP only vars
    brokers = None
    use_ssl = None
    # Set a deafault fot AMS only vars
    token = None
    project = None
    # Shared vars are not set here, they must have
    # sensible defaults set in the config parsing

    # Check for pidfile
    pidfile = cp.get('daemon', 'pidfile')
    if os.path.exists(pidfile):
        print 'Cannot start SSM.  Pidfile %s already exists.' % pidfile
        sys.exit(1)
    
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
        print 'SSM will exit.'
        sys.exit(1)
        
    global log
    log = logging.getLogger('ssmreceive')
    
    log.info(LOG_BREAK)
    log.info('Starting receiving SSM version %s.%s.%s.', *__version__)

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

    if destination_type == 'STOMP-BROKER':
        # We are setting up an SSM to connect to an old style STOMP Broker
        # If we can't get a broker to connect to, we have to give up.
        try:
            bg = StompBrokerGetter(cp.get('broker', 'bdii'))
            use_ssl = cp.getboolean('broker', 'use_ssl')
            if use_ssl:
                service = STOMP_SSL_SERVICE
            else:
                service = STOMP_SERVICE
            brokers = bg.get_broker_hosts_and_ports(service, cp.get('broker', 'network'))
        except ConfigParser.NoOptionError, e:
            try:
                host = cp.get('broker', 'host')
                port = cp.get('broker', 'port')
                brokers = [(host, int(port))]
            except ConfigParser.NoOptionError:
                log.error('Options incorrectly supplied for either single broker \
                          or broker network.  Please check configuration')
                log.error('System will exit.')
                log.info(LOG_BREAK)
                sys.exit(1)
        except ldap.SERVER_DOWN, e:
            log.error('Could not connect to LDAP server: %s', e)
            log.error('System will exit.')
            log.info(LOG_BREAK)
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
            subscription = cp.get('AMS', 'subscription')
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
        check_crls = cp.getboolean('certificates', 'check_crls')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        check_crls = True

    log.info('The SSM will run as a daemon.')
    
    # We need to preserve the file descriptor for any log files.
    rootlog = logging.getLogger()
    log_files = [x.stream for x in rootlog.handlers]
    dc = DaemonContext(files_preserve=log_files)
        
    try:
        receiver = Ssm2(brokers,
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
                        subscription=subscription,
                        password=token,
                        listen=destination,
                        check_crls=check_crls,
                        pidfile=pidfile)
        
        log.info('Fetching valid DNs.')
        dns = get_dns(options.dn_file)
        receiver.set_dns(dns)
        
    except Exception, e:
        log.fatal('Failed to initialise SSM: %s', e)
        log.info(LOG_BREAK)
        sys.exit(1)

    try:
        # Note: because we need to be compatible with python 2.4, we can't use
        # with dc:
        # here - we need to call the open() and close() methods
        # manually.
        dc.open()
        receiver.startup()
        i = 0
        # The message listening loop.
        while True:

            time.sleep(1)
            if destination_type == 'ARGO-AMS':
                receiver.pull_msg_rest()

            if i % REFRESH_DNS == 0:
                log.info('Refreshing the valid DNs.')
                dns = get_dns(options.dn_file)
                receiver.set_dns(dns)

                if destination_type == 'STOMP-BROKER':
                    try:
                        log.info('Sending ping.')
                        receiver.send_ping()
                    except NotConnectedException:
                        log.error('Connection lost.')
                        receiver.shutdown()
                        dc.close()
                        log.info("Waiting for 10 minutes before restarting...")
                        time.sleep(10 * 60)
                        log.info('Restarting SSM.')
                        dc.open()
                        receiver.startup()
            i += 1
    
    except SystemExit, e:
        log.info('Received the shutdown signal: %s', e)
        receiver.shutdown()
        dc.close()
    except Exception, e:
        log.error('Unexpected exception: %s', e)
        log.error('Exception type: %s', e.__class__)
        log.error('The SSM will exit.')
        receiver.shutdown()
        dc.close()
        
    log.info('Receiving SSM has shut down.')
    log.info(LOG_BREAK)
    
    
if __name__ == '__main__':
    main()
