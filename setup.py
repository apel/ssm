"""A setup up script for the APEL-SSM."""
from setuptools import setup, find_packages

# required to parse the requiremnts.txt file
# from pip.req import parse_requirements

# parse_requirements() returns generator of pip.req.InstallRequirement objects
# install_requirements = parse_requirements("requirements.txt")
# print str(install_reqs).strip('[]')

# nned install_requirements as a list of requirements
# e.g. ['django==1.5.1', 'mezzanine==1.4.6']
# install_requirements = [str(ir.req) for ir in install_reqs]

setup(name='ssm',
      version='2.1.7-1',
      description=("Secure Stomp Messenger (SSM) is designed to simply send "
                   "messages using the STOMP protocol."),
      author='APEL',
      author_email='apel-admins@stfc.ac.uk',
      url='https://github.com/apel/ssm',
      download_url='https://github.com/apel/ssm/archive/2.1.7-1.zip',
      license='Apache License, version 2 - http://www.apache.org/licenses/',
      install_requires=['stomp.py<=3.1.6', 'python-ldap', 'dirq'],
      extras_require={
          'python-daemon': ['python-daemon'],
          'unittest2': ['unittest2'],
          'coveralls': ['coveralls'],
      },
      packages=find_packages('ssm'),  # include all packages under ssm
      package_dir={'': 'ssm'})  # tell distutils packages are under ssm
