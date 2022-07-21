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

"""Script to run a receiving SSM."""

from __future__ import print_function

import ssm.agents
from ssm import __version__, LOG_BREAK

import logging
import os
import sys
from optparse import OptionParser

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser


def main():
    """Set up connection, and listen for messages."""
    ver = "SSM %s.%s.%s" % __version__
    op = OptionParser(description=__doc__, version=ver)
    op.add_option('-c', '--config', help='location of config file',
                  default='/etc/apel/receiver.cfg')
    op.add_option('-d', '--dn_file',
                  help='location of the file containing valid DNs',
                  default='/etc/apel/dns')

    options, unused_args = op.parse_args()

    # Absolute file path required when refreshing dn_file, relative path resulted in an error. 
    options.dn_file = os.path.abspath(options.dn_file)

    cp = ConfigParser.ConfigParser({'use_ssl': 'true'})
    cp.read(options.config)

    # Check for pidfile
    pidfile = cp.get('daemon', 'pidfile')
    if os.path.exists(pidfile):
        print('Cannot start SSM.  Pidfile %s already exists.' % pidfile)
        sys.exit(1)

    ssm.agents.logging_helper(cp)

    log = logging.getLogger('ssmreceive')

    log.info(LOG_BREAK)
    log.info('Starting receiving SSM version %s.%s.%s.', *__version__)

    protocol = ssm.agents.get_protocol(cp, log)

    log.info('Setting up SSM with protocol: %s', protocol)

    brokers, project, token = ssm.agents.get_ssm_args(protocol, cp, log)

    ssm.agents.run_receiver(protocol, brokers, project, token,
                            cp, log, options.dn_file)


if __name__ == '__main__':
    main()
