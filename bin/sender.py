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

"""Script to run a sending SSM."""

from __future__ import print_function

import ssm.agents
from ssm import __version__, LOG_BREAK

from argparse import ArgumentParser
import logging
import os
import sys

import configparser


def main():
    """Set up connection, send all messages and quit."""
    ver = "SSM %s.%s.%s" % __version__
    default_conf_location = '/etc/apel/sender.cfg'
    arg_parser = ArgumentParser(description=__doc__)

    arg_parser.add_argument('-c', '--config',
                            help='location of config file, default path: '
                                  '%s' % default_conf_location,
                            default=default_conf_location)
    arg_parser.add_argument('-l', '--log_config',
                            help='DEPRECATED - location of logging config file',
                            default=None)
    arg_parser.add_argument('-v', '--version',
                            action='version',
                            version=ver)

    # Using the vars function to output a dict-like view rather than Namespace object.
    options = vars(arg_parser.parse_args())

    # Deprecating functionality.
    old_log_config_default_path = '/etc/apel/logging.cfg'
    if (os.path.exists(old_log_config_default_path) or options['log_config'] is not None):
        logging.warning('Separate logging config file option has been deprecated.')

    # Check if config file exists using os.path.isfile function.
    if os.path.isfile(options['config']):
        cp = configparser.ConfigParser({'use_ssl': 'true'})
        cp.read(options['config'])
    else:
        print("Config file not found at", options['config'])
        sys.exit(1)

    ssm.agents.logging_helper(cp)

    log = logging.getLogger('ssmsend')

    log.info(LOG_BREAK)
    log.info('Starting sending SSM version %s.%s.%s.', *__version__)

    protocol = ssm.agents.get_protocol(cp, log)

    log.info('Setting up SSM with protocol: %s', protocol)

    brokers, project, token = ssm.agents.get_ssm_args(protocol, cp, log)

    ssm.agents.run_sender(protocol, brokers, project, token, cp, log)


if __name__ == '__main__':
    main()
