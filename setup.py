"""A setup script for APEL SSM.

This script installs the APEL SSM library, sender and reciever. This
should be similar to installing the RPM apel-ssm, although there
may be some differences.

Known differences are:
- the RPM installs pyc and pyo files, whereas this script does not.
- this script will not install system specific init style files.

Usage: 'python setup.py install'

Requires setuptools.
"""

from os import remove
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
        copyfile('scripts/apel-ssm.logrotate', 'conf/apel-ssm')
        copyfile('README.md', 'apel-ssm')

    # conf_files will later be copied to conf_dir
    conf_dir = '/etc/apel/'
    conf_files = ['conf/receiver.cfg',
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
          install_requires=[
              'cryptography==3.3.0',
              'stomp.py<5.0.0',
              'python-ldap<3.4.0',
              'setuptools',
              'pyopenssl<=21.0.0',
          ],
          extras_require={
              'AMS': ['argo-ams-library', 'certifi<2020.4.5.2', ],
              'daemon': ['python-daemon<=2.3.0', ],
              'dirq': ['dirq'],
          },
          packages=find_packages(exclude=['bin', 'test']),
          scripts=['bin/ssmreceive', 'bin/ssmsend'],
          data_files=[(conf_dir, conf_files),
                      ('/etc/logrotate.d', ['conf/apel-ssm']),
                      ('/usr/share/doc/apel-ssm', ['apel-ssm']),
                      # Create empty directories
                      ('/var/log/apel', []),
                      ('/var/run/apel', []),
                      ('/var/spool/apel', [])],
          # zip_safe allows setuptools to install the project
          # as a zipfile, for maximum performance!
          # We have disabled this feature so installing via the setup
          # script is similar to installing the RPM apel-ssm
          zip_safe=False,
          )

    # Remove temporary files with deployment names
    if 'install' in sys.argv:
        remove('bin/ssmreceive')
        remove('bin/ssmsend')
        remove('conf/apel-ssm')
        remove('apel-ssm')


if __name__ == "__main__":
    main()
