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
import sys
import time

import configparser

try:
    from daemon import DaemonContext
except ImportError:
    # A error is logged and the receiver exits later if DaemonContext is
    # requested but not installed.
    DaemonContext = None

from stomp.exception import NotConnectedException
try:
    from argo_ams_library import (AmsConnectionException, AmsTimeoutException,
                                  AmsBalancerException)
except ImportError:
    # ImportError is raised when Ssm2 initialised if AMS is requested but lib
    # not installed.
    class AmsConnectionException(Exception):
        """Placeholder exception if argo_ams_library not used."""
        pass

from ssm import set_up_logging, LOG_BREAK
from ssm.ssm2 import Ssm2, Ssm2Exception
from ssm.crypto import CryptoException, get_certificate_subject, _from_file

# How often (in seconds) to read the list of valid DNs.
REFRESH_DNS = 600


def logging_helper(cp):
    """Take config parser object and set up root logger."""
    try:
        set_up_logging(
            cp.get('logging', 'logfile'),
            cp.get('logging', 'level'),
            cp.getboolean('logging', 'console')
        )
    except (configparser.Error, ValueError, IOError) as err:
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
            raise configparser.NoSectionError('sender or receiver')

        if protocol not in (Ssm2.STOMP_MESSAGING, Ssm2.AMS_MESSAGING):
            raise ValueError

    except (configparser.NoSectionError, configparser.NoOptionError):
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

        try:
            host = cp.get('broker', 'host')
            port = cp.get('broker', 'port')
            brokers = [(host, int(port))]
        except configparser.NoOptionError:
            log.error('Host options incorrectly supplied for message broker '
                      'or AMS endpoint. Please check configuration.')
            log.error('System will exit.')
            log.info(LOG_BREAK)
            print('SSM failed to start.  See log file for details.')
            sys.exit(1)

    elif protocol == Ssm2.AMS_MESSAGING:
        # Then we are setting up an SSM to connect to a AMS.

        try:
            # We only need a hostname, not a port
            host = cp.get('broker', 'host')
            # Use brokers variable so subsequent code is not dependant on
            # the exact destination type.
            brokers = [host]

        except configparser.NoOptionError:
            log.error('The host must be specified when connecting to AMS, '
                      'please check your configuration')
            log.error('System will exit.')
            log.info(LOG_BREAK)
            print('SSM failed to start.  See log file for details.')
            sys.exit(1)

        # Attempt to configure AMS project variable.
        try:
            project = cp.get('messaging', 'ams_project')

        except (configparser.Error, ValueError, IOError) as err:
            # A project is needed to successfully send to an
            # AMS instance, so log and then exit on an error.
            log.error('Error configuring AMS values: %s', err)
            log.error('SSM will exit.')
            print('SSM failed to start.  See log file for details.')
            sys.exit(1)

        try:
            token = cp.get('messaging', 'token')
        except (configparser.Error, ValueError, IOError) as err:
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
            except configparser.NoOptionError:
                # If option not set, resort to value of verify_server_cert set above.
                pass
        except configparser.NoOptionError:
            log.info('No server certificate supplied.  Will not encrypt messages.')

        try:
            destination = cp.get('messaging', 'destination')
            if destination == '':
                raise Ssm2Exception('No destination queue is configured.')
        except configparser.NoOptionError as e:
            raise Ssm2Exception(e)

        # Determine what type of message store we are interacting with,
        # i.e. a dirq QueueSimple object or a plain MessageDirectory directory.
        try:
            path_type = cp.get('messaging', 'path_type')
        except configparser.NoOptionError:
            log.info('No path type defined, assuming dirq.')
            path_type = 'dirq'

        host_cert = cp.get('certificates', 'certificate')
        host_dn = get_certificate_subject(_from_file(host_cert))
        log.info('Messages will be signed using %s', host_dn)

        if server_cert == host_cert:
            raise Ssm2Exception(
                "server certificate is the same as host certificate in config file. "
                "Do you really mean to encrypt messages with this certificate?"
            )

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
        sender_failed = True
    except Exception as e:
        print('SSM failed to complete successfully.  See log file for details.')
        log.exception('Unexpected exception in SSM. See traceback below.')
        sender_failed = True
    else:
        sender_failed = False

    try:
        sender.close_connection()
    except UnboundLocalError:
        # SSM not set up.
        pass

    log.info('SSM has shut down.')
    log.info(LOG_BREAK)
    if sender_failed:
        sys.exit(1)


def run_receiver(protocol, brokers, project, token, cp, log, dn_file):
    """Run Ssm2 as a receiver daemon."""
    if DaemonContext is None:
        log.error("Receiving SSMs must use python-daemon, but the "
                  "python-daemon module wasn't found.")
        log.error("System will exit.")
        log.info(LOG_BREAK)
        sys.exit(1)

    log.info('The SSM will run as a daemon.')

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

        log.info('Fetching banned DNs.')
        banned_dns = get_banned_dns(log, cp)
        ssm.set_banned_dns(banned_dns)

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

            except (NotConnectedException, AmsConnectionException,
                    AmsTimeoutException, AmsBalancerException) as error:

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
        receiver_failed = True
    except Exception as e:
        log.exception('Unexpected exception in SSM. See traceback below.')
        log.error('The SSM will exit.')
        ssm.shutdown()
        dc.close()
        receiver_failed = True
    # Currently won't run the else statement due to the while loop in the reciever
    # Leaving here in case of future refactoring, but commented out so the unreachable
    # code isn't flagged by tests
    # else:
    #   receiver_failed = False

    log.info('Receiving SSM has shut down.')
    log.info(LOG_BREAK)
    if receiver_failed:
        sys.exit(1)


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


def get_banned_dns(log, cp):
    """Retrieve the list of banned dns"""
    banned_dns = []
    try:
        banned_dns_path = cp.get('auth', 'banned-dns')
        banned_dns_file = os.path.normpath(
            os.path.expandvars(banned_dns_path))
    except ConfigParser.NoOptionError:
        banned_dns_file = None

    with open(banned_dns_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.isspace() or line.strip().startswith('#'):
                continue
            elif line.strip().startswith('/'):
                banned_dns.append(line.strip())
            else:
                log.warning('DN in banned dns list is not in '
                            'the correct format: %s', line)

    return banned_dns
