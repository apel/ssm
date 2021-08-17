#!/usr/bin/env python

# Copyright 2021 UK Research and Innovation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Code for sender and receiver messaging agents/clients."""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import ldap
import os
import sys
import time

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

try:
    from daemon import DaemonContext
except ImportError:
    # A error is logged and the receiver exits later if DaemonContext is
    # requested but not installed.
    DaemonContext = None

from stomp.exception import NotConnectedException
try:
    from argo_ams_library import AmsConnectionException
except ImportError:
    # ImportError is raised when Ssm2 initialised if AMS is requested but lib
    # not installed.
    class AmsConnectionException(Exception):
        """Placeholder exception if argo_ams_library not used."""
        pass

from ssm import set_up_logging, LOG_BREAK
from ssm.ssm2 import Ssm2, Ssm2Exception
from ssm.crypto import CryptoException, get_certificate_subject, _from_file
from ssm.brokers import StompBrokerGetter, STOMP_SERVICE, STOMP_SSL_SERVICE

# How often (in seconds) to read the list of valid DNs.
REFRESH_DNS = 600


def logging_helper(cp, log_manual_path=''):
    """Take config parser object and set up root logger."""
    try:
        if os.path.exists(log_manual_path):
            logging.cp.fileConfig(log_manual_path)
        else:
            set_up_logging(cp.get('logging', 'logfile'),
                           cp.get('logging', 'level'),
                           cp.getboolean('logging', 'console'))
    except (ConfigParser.Error, ValueError, IOError) as err:
        print('Error configuring logging: %s' % err)
        print('The system will exit.')
        sys.exit(1)


def get_protocol(cp, log):
    """Get the protocol from a ConfigParser object, defaulting to STOMP."""
    try:
        if 'sender' in cp.sections():
            protocol = cp.get('sender', 'protocol')
        elif 'receiver' in cp.sections():
            protocol = cp.get('receiver', 'protocol')
        else:
            raise ConfigParser.NoSectionError('sender or receiver')

        if protocol not in (Ssm2.STOMP_MESSAGING, Ssm2.AMS_MESSAGING):
            raise ValueError

    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        # If the newer configuration setting 'protocol' is not set, use 'STOMP'
        # for backwards compatability.
        protocol = Ssm2.STOMP_MESSAGING
        log.warning("No option set for 'protocol'. Defaulting to %s.", protocol)
    except ValueError:
        log.critical("Invalid protocol '%s' set. Must be either '%s' or '%s'.",
                     protocol, Ssm2.STOMP_MESSAGING, Ssm2.AMS_MESSAGING)
        log.critical('SSM will exit.')
        print('SSM failed to start.  See log file for details.')
        sys.exit(1)

    return protocol


def get_ssm_args(protocol, cp, log):
    """Return brokers, project, and token from config based on protocol."""
    if protocol == Ssm2.STOMP_MESSAGING:
        # Set defaults for AMS variables that Ssm2 constructor requires below.
        project = None
        token = ''

        use_ssl = cp.getboolean('broker', 'use_ssl')
        if use_ssl:
            service = STOMP_SSL_SERVICE
        else:
            service = STOMP_SERVICE

        # If we can't get a broker to connect to, we have to give up.
        try:
            bdii_url = cp.get('broker', 'bdii')
            log.info('Retrieving broker details from %s ...', bdii_url)
            bg = StompBrokerGetter(bdii_url)
            brokers = bg.get_broker_hosts_and_ports(service, cp.get('broker',
                                                                    'network'))
            log.info('Found %s brokers.', len(brokers))
        except ConfigParser.NoOptionError as e:
            try:
                host = cp.get('broker', 'host')
                port = cp.get('broker', 'port')
                brokers = [(host, int(port))]
            except ConfigParser.NoOptionError:
                log.error('Options incorrectly supplied for either single '
                          'broker or broker network. '
                          'Please check configuration')
                log.error('System will exit.')
                log.info(LOG_BREAK)
                print('SSM failed to start.  See log file for details.')
                sys.exit(1)
        except ldap.LDAPError as e:
            log.error('Could not connect to LDAP server: %s', e)
            log.error('System will exit.')
            log.info(LOG_BREAK)
            print('SSM failed to start.  See log file for details.')
            sys.exit(1)

    elif protocol == Ssm2.AMS_MESSAGING:
        # Then we are setting up an SSM to connect to a AMS.

        # TODO: See if setting use_ssl directly in Ssm2 constructor is ok.
        # 'use_ssl' isn't checked when using AMS (SSL is always used), but it
        # is needed for the call to the Ssm2 constructor below.
        use_ssl = None
        try:
            # We only need a hostname, not a port
            host = cp.get('broker', 'host')
            # Use brokers variable so subsequent code is not dependant on
            # the exact destination type.
            brokers = [host]

        except ConfigParser.NoOptionError:
            log.error('The host must be specified when connecting to AMS, '
                      'please check your configuration')
            log.error('System will exit.')
            log.info(LOG_BREAK)
            print('SSM failed to start.  See log file for details.')
            sys.exit(1)

        # Attempt to configure AMS project variable.
        try:
            project = cp.get('messaging', 'ams_project')

        except (ConfigParser.Error, ValueError, IOError) as err:
            # A project is needed to successfully send to an
            # AMS instance, so log and then exit on an error.
            log.error('Error configuring AMS values: %s', err)
            log.error('SSM will exit.')
            print('SSM failed to start.  See log file for details.')
            sys.exit(1)

        try:
            token = cp.get('messaging', 'token')
        except (ConfigParser.Error, ValueError, IOError) as err:
            # A token is not necessarily needed, if the cert and key can be
            # used by the underlying auth system to get a suitable token.
            log.info('No AMS token provided, using cert/key pair instead.')
            # Empty string used by AMS to define absence of token.
            token = ''

    if len(brokers) == 0:
        log.error('No brokers available.')
        log.error('System will exit.')
        log.info(LOG_BREAK)
        sys.exit(1)

    return brokers, project, token


def run_sender(protocol, brokers, project, token, cp, log):
    """Run Ssm2 as a sender."""
    try:
        server_cert = None
        verify_server_cert = True
        try:
            server_cert = cp.get('certificates', 'server_cert')
            server_dn = get_certificate_subject(_from_file(server_cert))
            log.info('Messages will be encrypted using %s', server_dn)
            try:
                verify_server_cert = cp.getboolean('certificates', 'verify_server_cert')
            except ConfigParser.NoOptionError:
                # If option not set, resort to value of verify_server_cert set above.
                pass
        except ConfigParser.NoOptionError:
            log.info('No server certificate supplied.  Will not encrypt messages.')

        # Check that the destination queue is configured and log the queue
        check_destination(cp, log)

        # Determine what type of message store we are interacting with,
        # i.e. a dirq QueueSimple object or a plain MessageDirectory directory.
        try:
            path_type = cp.get('messaging', 'path_type')
        except ConfigParser.NoOptionError:
            log.info('No path type defined, assuming dirq.')
            path_type = 'dirq'

        host_cert = cp.get('certificates', 'certificate')
        host_dn = get_certificate_subject(_from_file(host_cert))
        log.info('Messages will be signed using %s', host_dn)

        sender = Ssm2(brokers,
                      cp.get('messaging', 'path'),
                      path_type=path_type,
                      cert=host_cert,
                      key=cp.get('certificates', 'key'),
                      dest=cp.get('messaging', 'destination'),
                      use_ssl=cp.getboolean('broker', 'use_ssl'),
                      capath=cp.get('certificates', 'capath'),
                      enc_cert=server_cert,
                      verify_enc_cert=verify_server_cert,
                      protocol=protocol,
                      project=project,
                      token=token)

        if sender.has_msgs():
            sender.handle_connect()
            sender.send_all()
            log.info('SSM run has finished.')
        else:
            log.info('No messages found to send.')

    except (Ssm2Exception, CryptoException) as e:
        print('SSM failed to complete successfully.  See log file for details.')
        log.error('SSM failed to complete successfully: %s', e)
    except Exception as e:
        print('SSM failed to complete successfully.  See log file for details.')
        log.error('Unexpected exception in SSM: %s', e)
        log.error('Exception type: %s', e.__class__)

    try:
        sender.close_connection()
    except UnboundLocalError:
        # SSM not set up.
        pass

    log.info('SSM has shut down.')
    log.info(LOG_BREAK)


def run_receiver(protocol, brokers, project, token, cp, log, dn_file):
    """Run Ssm2 as a receiver daemon."""
    if DaemonContext is None:
        log.error("Receiving SSMs must use python-daemon, but the "
                  "python-daemon module wasn't found.")
        log.error("System will exit.")
        log.info(LOG_BREAK)
        sys.exit(1)

    log.info('The SSM will run as a daemon.')

    # Check that the destination queue is configured and log the queue
    check_destination(cp, log)

    # We need to preserve the file descriptor for any log files.
    rootlog = logging.getLogger()
    log_files = [x.stream for x in rootlog.handlers]
    dc = DaemonContext(files_preserve=log_files)

    try:
        ssm = Ssm2(brokers,
                   cp.get('messaging', 'path'),
                   cert=cp.get('certificates', 'certificate'),
                   key=cp.get('certificates', 'key'),
                   listen=cp.get('messaging', 'destination'),
                   use_ssl=cp.getboolean('broker', 'use_ssl'),
                   capath=cp.get('certificates', 'capath'),
                   check_crls=cp.getboolean('certificates', 'check_crls'),
                   pidfile=cp.get('daemon', 'pidfile'),
                   protocol=protocol,
                   project=project,
                   token=token)

        log.info('Fetching valid DNs.')
        dns = get_dns(dn_file, log)
        ssm.set_dns(dns)

    except Exception as e:
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
            try:
                time.sleep(0.1)
                if protocol == Ssm2.AMS_MESSAGING:
                    # We need to pull down messages as part of
                    # this loop when using AMS.
                    ssm.pull_msg_ams()

                if i % (REFRESH_DNS * 10) == 0:
                    log.info('Refreshing valid DNs and then sending ping.')
                    dns = get_dns(dn_file, log)
                    ssm.set_dns(dns)

                    if protocol == Ssm2.STOMP_MESSAGING:
                        ssm.send_ping()

            except (NotConnectedException, AmsConnectionException) as error:
                log.warning('Connection lost.')
                log.debug(error)
                ssm.shutdown()
                dc.close()
                log.info("Waiting for 10 minutes before restarting...")
                time.sleep(10 * 60)
                log.info('Restarting SSM.')
                dc.open()
                ssm.startup()

            i += 1

    except SystemExit as e:
        log.info('Received the shutdown signal: %s', e)
        ssm.shutdown()
        dc.close()
    except Exception as e:
        log.error('Unexpected exception: %s', e)
        log.error('Exception type: %s', e.__class__)
        log.error('The SSM will exit.')
        ssm.shutdown()
        dc.close()

    log.info('Receiving SSM has shut down.')
    log.info(LOG_BREAK)


def get_dns(dn_file, log):
    """Retrieve a list of DNs from a file."""
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
                log.warning('DN in incorrect format: %s', line)
    finally:
        if f is not None:
            f.close()
    # If no valid DNs, SSM cannot receive any messages.
    if len(dns) == 0:
        raise Ssm2Exception('No valid DNs found in %s.  SSM will not start' % dn_file)

    log.debug('%s DNs found.', len(dns))
    return dns


def check_destination(cp, log):
    try:
        destination = cp.get('messaging', 'destination')
        if destination == '':
            raise Ssm2Exception('No destination queue is configured.')

        log.info('Configured destination queue: %s', destination)
    except ConfigParser.NoOptionError as e:
        raise Ssm2Exception(e)
