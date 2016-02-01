"""A setup up script for the APEL-SSM."""
import sys
import os
from setuptools import setup, find_packages


def main():
    """Called when run as script, i.e. "python setup.py install"."""
    bin_dir = os.path.join(sys.prefix, "bin")
    bin_files = ['bin/apel-ssm', 'bin/receiver.py', 'bin/sender.py']

    setup(name='ssm',
          version='2.1.7-1',
          description=("Secure Stomp Messenger (SSM) is designed to simply "
                       "send messages using the STOMP protocol."),
          author='APEL',
          author_email='apel-admins@stfc.ac.uk',
          url='https://github.com/apel/ssm',
          download_url='https://github.com/apel/ssm/archive/2.1.7-1.zip',
          license='Apache License, v2 - http://www.apache.org/licenses/',
          install_requires=['stomp.py<=3.1.6', 'python-ldap', 'dirq'],
          extras_require={
              'python-daemon': ['python-daemon'],
              'unittest2': ['unittest2'],
              'coveralls': ['coveralls'],
          },
          packages=find_packages('ssm'),  # include all packages under ssm
          package_dir={'': 'ssm'},  # tell distutils packages are under ssm
          data_files=[(bin_dir, bin_files)])

if __name__ == "__main__":
    main()
