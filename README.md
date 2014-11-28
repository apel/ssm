# Secure Stomp Messenger

[![Build Status](https://travis-ci.org/apel/ssm.svg?branch=dev)](https://travis-ci.org/apel/ssm)
[![Coverage Status](https://coveralls.io/repos/apel/ssm/badge.png?branch=dev)](https://coveralls.io/r/apel/ssm?branch=dev)
[![Code Health](https://landscape.io/github/apel/ssm/dev/landscape.png)](https://landscape.io/github/apel/ssm/dev)

Secure Stomp Messenger (SSM) is designed to simply send messages
using the STOMP protocol.  Messages are signed and may be encrypted
during transit.  Persistent queues should be used to guarantee
delivery.

SSM is written in python.  Packages are available for SL5 and SL6.

For more about SSM, see the [EGI wiki](https://wiki.egi.eu/wiki/APEL/SSM).


## Installing the RPM

### Prerequisites

The EPEL repository must be enabled.  This can be done by installing
the RPM for your version of SL, which is available on this page:
http://fedoraproject.org/wiki/EPEL

The python stomp library (N.B. version 4 is currently not supported)
* `yum install stomppy`

The python daemon library
* `yum install python-daemon`

The python ldap library
* `yum install python-ldap`

The python dirq library
* `yum install python-dirq`

You need a certificate and key in PEM format accessible to the SSM.
There are a number of ways to do this.  One is to make a copy of the
hostcert and hostkey files, owned by the apel user (created later):
 * /etc/grid-security/hostcert-ssm.pem
 * /etc/grid-security/hostkey-ssm.pem
These are the default settings in the configuration file ssm.cfg.
You can use a different configuration if you prefer.

You need certificates against which you're going to verify any certs
you use or receive in the directory /etc/grid-security/certificates (or other
configured location).  The best way to do this for EGI is to install the
ca-policy-egi-core package:
* `cd /etc/yum.repos.d/`
* `wget http://repository.egi.eu/sw/production/cas/1/current/repo-files/EGI-trustanchors.repo`
* `yum install ca-policy-egi-core`

If you want to check CRLs when verifying certificates, you need
fetch_crl installed:
* `yum install fetch-crl`
* `service fetch-crl-cron start`
* `chkconfig fetch-crl-cron on`

fetch-crl must have run once for the certificates to be verified
successfully.

### Installation

* `rpm -i apelssm-<version>.noarch.rpm`

### What the RPM does

The RPM carries out a number of steps to run the SSM in a specific way.

1. It installs the core files in the python libraries directory
2. It installs scripts in /usr/bin
3. It installs configuration files in /etc/apel
4. It creates the messages directory /var/spool/apel/
5. It creates the log directory /var/log/apel/
6. It creates the pidfile directory /var/run/apel/
7. It installs a service script in /etc/init.d/


## Configuring the SSM

Create the apel user:
* `useradd -r apel`

Ensure that the apel user running the SSM has access to the following:
* the host certificate and key, or a copy
* `chown apel:apel /var/spool/apel/`
* `chown apel:apel /var/log/apel/`
* `chown apel:apel /var/run/apel`

The configuration files are in /etc/apel/.  The default
configuration will send messages to the test apel server.


## Adding Files

There are two ways to add files to be sent:

### Manual

All file and directory names must use hex characters: `[0-9a-f]`.

 * Create a directory within /var/spool/apel/outgoing with a name
   of EIGHT hex characters e.g. `12345678`
 * Put files in this directory with names of FOURTEEN hex 
   e.g. `1234567890abcd`

### Programmatic

Use the python or perl dirq libraries:
 * python: http://pypi.python.org/pypi/dirq
 * perl: http://search.cpan.org/~lcons/Directory-Queue/

Create a QueueSimple object with path /var/spool/apel/outgoing/ and 
add your messages.


## Running the SSM

###  Sender

 * Run 'ssmsend'
 * SSM will pick up any messages and send them to the configured
   queue on the configured broker
   
### Receiver (service)
  
 * Run `service apelssm start`
 * If this fails, check /var/log/apel/ssmreceive.log for details
 * To stop, run `service apelssm stop`

### Receiver (manual)

 * Run 'ssmreceive'
 * SSM will receive any messages on the specified queue and
   write them to the filesystem
 * To stop, run ```'kill `cat /var/run/apel/ssm.pid`'```

## Removing the RPM

* `rpm -e apelssm`

## Cleaning the system

* `yum remove stomppy`
* `yum remove python-daemon`
* `yum remove python-ldap`

* `rm -rf /var/spool/apel`
* `rm -rf /var/log/apel`
* `rm -rf /var/run/apel`

* revert any changes to or copies of the host certificate and key
