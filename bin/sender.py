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

import agents
from ssm import __version__, LOG_BREAK

import logging
from optparse import OptionParser

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser


def main():
    """Set up connection, send all messages and quit."""
    ver = "SSM %s.%s.%s" % __version__
    op = OptionParser(description=__doc__, version=ver)
    op.add_option('-c', '--config', help='location of config file',
                  default='/etc/apel/sender.cfg')
    op.add_option('-l', '--log_config',
                        help='location of logging config file (optional)',
                        default='/etc/apel/logging.cfg')
    (options, unused_args) = op.parse_args()

    cp = ConfigParser.ConfigParser({'use_ssl': 'true'})
    cp.read(options.config)

    agents.logging_helper(cp, options.log_config)

    log = logging.getLogger('ssmsend')

    log.info(LOG_BREAK)
    log.info('Starting sending SSM version %s.%s.%s.', *__version__)

    protocol = agents.get_protocol(cp, log)

    log.info('Setting up SSM with protocol: %s', protocol)

    brokers, project, token = agents.get_ssm_args(protocol, cp, log)

    agents.run_sender(protocol, brokers, project, token, cp, log)


if __name__ == '__main__':
    main()
