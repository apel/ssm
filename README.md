# Secure STOMP Messenger

[![Build Status](https://travis-ci.org/apel/ssm.svg?branch=dev)](https://travis-ci.org/apel/ssm)
[![Coverage Status](https://coveralls.io/repos/github/apel/ssm/badge.svg?branch=dev)](https://coveralls.io/github/apel/ssm?branch=dev)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/9d2b1c88ab844f0081e5fafab49b269d)](https://www.codacy.com/gh/apel/ssm/dashboard)
[![Maintainability](https://api.codeclimate.com/v1/badges/34aa04f3583afce2ceb2/maintainability)](https://codeclimate.com/github/apel/ssm/maintainability)

Secure STOMP Messenger (SSM) is designed to simply send messages
using the [STOMP protocol](http://stomp.github.io/) or via the ARGO Messaging Service (AMS).
Messages are signed and may be encrypted during transit.
Persistent queues should be used to guarantee delivery.

SSM is written in Python. Packages are available for RHEL 7, and Ubuntu Trusty.

For more information about SSM, see the [EGI wiki](https://wiki.egi.eu/wiki/APEL/SSM).

## Acknowledgements

<span>
  <img alt="STFC logo" src="https://github.com/GOCDB/gocdb/blob/dev/htdocs/images/logos/ukri_stfc.png" height="57" />
  <img alt="EU flag" src="https://github.com/GOCDB/gocdb/blob/dev/htdocs/images/flags/eu.png" height="51" />
  <img alt="EOSC-hub logo" src="https://github.com/GOCDB/gocdb/blob/dev/htdocs/images/logos/eosc_future.png" height="57" />
</span>

SSM is provided by [STFC](https://stfc.ukri.org/), a part of [UK Research and Innovation](https://www.ukri.org/), and is co-funded by the [EOSC-hub](https://www.eosc-hub.eu/) project (Horizon 2020) under Grant number 777536. Licensed under the [Apache 2 License](http://www.apache.org/licenses/LICENSE-2.0).

## Installing the RPM

### Prerequisites

The EPEL repository must be enabled.  This can be done by installing
the RPM for your version of SL, which is available on this page:
http://fedoraproject.org/wiki/EPEL
You will also need to have the OpenSSL library installed. Other prerequisites are listed below.

The Python STOMP library (N.B. versions between 3.1.1 (inclusive) and 5.0.0
(exclusive) are currently supported)
* `yum install stomppy`

The Python AMS library. This is only required if you want to use AMS. See here for details on obtaining an RPM: https://github.com/ARGOeu/argo-ams-library/

The Python ldap library
* `yum install python-ldap`

Optionally, the Python dirq library (N.B. this is only required if your messages
are stored in a dirq structure)
* `yum install python-dirq`

The Python daemon library (N.B. installing this library is only required when
using the SSM as a receiver)
* `yum install python-daemon`

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

1. It installs the core files in the Python libraries directory
2. It installs scripts in /usr/bin
3. It installs configuration files in /etc/apel
4. It creates the messages directory /var/spool/apel/
5. It creates the log directory /var/log/apel/
6. It creates the pidfile directory /var/run/apel/
7. It installs a service script in /etc/init.d/

## Installing the DEB

### Installation
Install APEL SSM:
* `dpkg -i apel-ssm_<version>_all.deb`

Install any missing system packages needed for the SSM:
* `apt-get -f install`

Install any missing Python requirements that don't have system packages:
* `pip install "stomp.py<5.0.0" dirq`

If you wish to run the SSM as a receiver, you will also need to install the python-daemon system package:
* `apt-get install python-daemon`

### What the DEB does

The DEB carries out a number of steps to run the SSM in a specific way.

1. It installs the core files in the Python libraries directory
2. It installs scripts in /usr/bin
3. It installs configuration files in /etc/apel
4. It creates the messages directory /var/spool/apel/
5. It creates the log directory /var/log/apel/
6. It creates the pidfile directory /var/run/apel/

## Configuring the SSM

Create the apel user:
* `useradd -r apel`

Ensure that the apel user running the SSM has access to the following:
* the host certificate and key, or a copy
* `chown apel:apel /var/spool/apel/`
* `chown apel:apel /var/log/apel/`
* `chown apel:apel /var/run/apel`

The configuration files are in /etc/apel/.  The default
configuration will send messages to the test APEL server.


## Adding Files

There are multiple manual and programmatic ways to add files to be sent:

### Manual

#### With the dirq module
All file and directory names must use hex characters: `[0-9a-f]`.

 * Create a directory within /var/spool/apel/outgoing with a name
   of EIGHT hex characters e.g. `12345678`
 * Put files in this directory with names of FOURTEEN hex
   e.g. `1234567890abcd`

#### Without the dirq module
Ensure `path_type: directory` is set in your `sender.cfg`.
Then add messages as files to `/var/spool/apel/outgoing`,
there are no restrictions on the file names used.

### Programmatic

#### With the dirq module
Use the Python or Perl dirq libraries:
 * Python: http://pypi.python.org/pypi/dirq
 * Perl: http://search.cpan.org/~lcons/Directory-Queue/

Create a QueueSimple object with path /var/spool/apel/outgoing/ and
add your messages.

#### Without the dirq module
Use the `MessageDirectory` class provided in `ssm.message_directory`.

Create a `MessageDirectory` object with path `/var/spool/apel/outgoing/` and
add your messages using the `add` method.

## Running the SSM

### Sender (sending via the EGI message brokers)

 * Run 'ssmsend'
 * SSM will pick up any messages and send them to the configured
   queue on the configured broker

### Sender (sending via the ARGO Messaging Service (AMS))

 * Edit your sender configuration, usually under `/etc/apel/sender.cfg`, as per the [migration instructions](migrating_to_ams.md#sender) with some minor differences:
   * There is no need to add the `[sender]` section as it already exists. Instead change the `protocol` to `AMS`.
   * Set `ams_project` to the appropriate project.
 * Then run 'ssmsend'. SSM will pick up any messages and send them via the ARGO Messaging Service.

### Sender (container)
 * Download the example [configuration file](conf/sender.cfg)
 * Edit the downloaded `sender.cfg` file as above for sending either via the [EGI message brokers](README.md#sender-sending-via-the-egi-message-brokers) or the [ARGO Messaging Service](README.md#sender-sending-via-the-argo-messaging-service-ams).
 * Run the following docker command to send
 ```
 docker run \
     -d --entrypoint ssmsend \
     -v /path/to/downloaded/config/sender.cfg:/etc/apel/sender.cfg \
     -v /path/to/read/messages:/var/spool/apel/outgoing \
     -v /etc/grid-security:/etc/grid-security \
     -v /path/to/persistently/log:/var/log/apel \
     ghcr.io/apel/ssm
 ```
 * The line `-v /path/to/persistently/log:/var/log/apel \` is only required if you want to access the sender log as a file. If `console: true` is set in your `sender.cfg`, the container will also log to stdout/stderr.

### Receiver (service)

 * Run `service apelssm start`
 * If this fails, check /var/log/apel/ssmreceive.log for details
 * To stop, run `service apelssm stop`

### Receiver (container)
 * Download the example [configuration file](conf/receiver.cfg)
 * Edit the downloaded receiver.cfg file to configure the queue and broker
 * Run the following docker command to launch containerized receiver process
 ```
 docker run \
     -d --entrypoint ssmreceive \
     -v /path/to/downloaded/config/sender.cfg:/etc/apel/sender.cfg \
     -v /path/to/read/messages:/var/spool/apel/outgoing \
     -v /path/to/dns/file:/etc/apel/dns \
     -v /etc/grid-security:/etc/grid-security \
     -v /path/to/persistently/log:/var/log/apel \
     ghcr.io/apel/ssm
 ```
  * The line `-v /path/to/persistently/log:/var/log/apel \` is only required if you want to access the receiver log as a file. If `console: true` is set in your `receiver.cfg`, the container will also log to stdout/stderr.

### Receiver (manual)

 * Run 'ssmreceive'
 * SSM will receive any messages on the specified queue and
   write them to the filesystem
 * To stop, run ```'kill `cat /var/run/apel/ssm.pid`'```

### Receiver (receiving via the ARGO Messaging Service (AMS))

 * Edit your receiver configuration, usually under `/etc/apel/receiver.cfg`, as per the [migration instructions](migrating_to_ams.md#receiver) with some minor differences:
   * There is no need to add the `[receiver]` section as it already exists. Instead change the `protocol` to `AMS`.
   * Set `ams_project` to the appropriate project.
 * Then run your receiver ([as a service](README.md#receiver-service), [as a container](README.md#receiver-container) or [manually](README.md#receiver-manual)) as above.

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
