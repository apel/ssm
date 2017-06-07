"""A setup script for APEL SSM.

This script installs the APEL SSM library, sender and reciever. This
should be similar to installing the RPM apel-ssm, although there
may be some differences. A known difference is the RPM installs pyc
and pyo files, whereas this script does not.

Usage: 'python setup.py install'

Requires setuptools.
"""

from os import remove, path, makedirs
from shutil import copyfile
import sys

from setuptools import setup, find_packages

from ssm import __version__


def main():
    """Called when run as script, e.g. 'python setup.py install'."""
    # Create temporary files with deployment names
    if 'install' in sys.argv:
        copyfile('bin/receiver.py', 'bin/ssmreceive')
        copyfile('bin/sender.py', 'bin/ssmsend')
        copyfile('conf/ssm.logrotate', 'conf/apel-ssm')
        copyfile('README.md', 'apel-ssm')

        if not path.exists('/var/log/apel'):
            makedirs('/var/log/apel')

        if not path.exists('/var/run/apel'):
            makedirs('/var/run/apel')

        if not path.exists('/var/spool/apel'):
            makedirs('/var/spool/apel')

    # conf_files will later be copied to conf_dir
    conf_dir = '/etc/apel/'
    conf_files = ['conf/logging.cfg',
                  'conf/receiver.cfg',
                  'conf/sender.cfg',
                  'conf/dns']

    # For 'python setup.py install | test' to
    # work (on Linux SL6), 'python-daemon'
    # must be installed or included
    # in install_required | tests_require
    setup(name='apel-ssm',
          version='%i.%i.%i' % __version__,
          description=("Secure Stomp Messenger (SSM) is designed to simply "
                       "send messages using the STOMP protocol."),
          author='APEL',
          author_email='apel-admins@stfc.ac.uk',
          url='http://apel.github.io/',
          download_url='https://github.com/apel/ssm/releases',
          license='Apache License, Version 2.0',
          install_requires=['stomp.py<=3.1.6', 'python-ldap', 'dirq'],
          extras_require={
              'python-daemon': ['python-daemon'],
          },
          packages=find_packages(exclude=['bin']),
          scripts=['bin/ssmreceive', 'bin/ssmsend'],
          data_files=[(conf_dir, conf_files),
                      ('/etc/logrotate.d', ['conf/apel-ssm']),
                      ('/etc/init.d', ['bin/apel-ssm']),
                      ('/usr/share/doc', ['apel-ssm'])],
          # zip_safe allows setuptools to install the project
          # as a zipfile, for maximum performance!
          # We have disabled this feature so installing via the setup
          # script is similar to installing the RPM apel-ssm
          zip_safe=False,
          # The following two settings allow the test suite
          # to be run via 'python setup.py test'

          # The test command runs the project's unit tests without
          # actually deploying it, by temporarily putting the project's
          # source on sys.path, after first running build_ext -i and
          # egg_info to ensure that any C extensions and
          # project metadata are up-to-date.

          # This does require a old version of unittest to work
          # on python2.6 (unittest2==0.5.1)
          # The python package where the tests are located
          test_suite='test',
          # the test requirements
          tests_require=['unittest2', 'mock'])

    # Remove temporary files with deployment names
    if 'install' in sys.argv:
        remove('bin/ssmreceive')
        remove('bin/ssmsend')
        remove('conf/apel-ssm')
        remove('apel-ssm')

if __name__ == "__main__":
    main()
