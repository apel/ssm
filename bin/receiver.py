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

    # If we can't get a broker to connect to, we have to give up.
    try:
        bg = StompBrokerGetter(cp.get('broker','bdii'))
        use_ssl = cp.getboolean('broker', 'use_ssl')
        if use_ssl:
            service = STOMP_SSL_SERVICE
        else:
            service = STOMP_SERVICE
        brokers = bg.get_broker_hosts_and_ports(service, cp.get('broker','network'))
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
        
    log.info('The SSM will run as a daemon.')
    
    # We need to preserve the file descriptor for any log files.
    rootlog = logging.getLogger()
    log_files = [x.stream for x in rootlog.handlers]
    dc = DaemonContext(files_preserve=log_files)
        
    try:
        ssm = Ssm2(brokers, 
                   cp.get('messaging','path'),
                   cert=cp.get('certificates','certificate'),
                   key=cp.get('certificates','key'),
                   listen=cp.get('messaging','destination'),
                   use_ssl=cp.getboolean('broker','use_ssl'),
                   capath=cp.get('certificates', 'capath'),
                   check_crls=cp.getboolean('certificates', 'check_crls'),
                   pidfile=pidfile)
        
        log.info('Fetching valid DNs.')
        dns = get_dns(options.dn_file)
        ssm.set_dns(dns)
        
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
        ssm.startup()
        i = 0
        # The message listening loop.
        while True:

            time.sleep(1)

            if i % REFRESH_DNS == 0:
                log.info('Refreshing the valid DNs.')
                dns = get_dns(options.dn_file)
                ssm.set_dns(dns)

                try:
                    log.info('Sending ping.')
                    ssm.send_ping()
                except NotConnectedException:
                    log.error('Connection lost.')
                    ssm.shutdown()
                    dc.close()
                    log.info('Restarting SSM.')
                    dc.open()
                    ssm.startup()

            i += 1

    except SystemExit, e:
        log.info('Received the shutdown signal: %s', e)
        ssm.shutdown()
        dc.close()
    except Exception, e:
        log.error('Unexpected exception: %s', e)
        log.error('Exception type: %s', e.__class__)
        log.error('The SSM will exit.')
        ssm.shutdown()
        dc.close()
        
    log.info('Receiving SSM has shut down.')
    log.info(LOG_BREAK)
    
    
if __name__ == '__main__':
    main()
