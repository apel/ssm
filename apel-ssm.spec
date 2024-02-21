# Conditionally define python_sitelib
%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif

Name:           apel-ssm
Version:        3.4.0
%define releasenumber 1
Release:        %{releasenumber}%{?dist}
Summary:        Secure stomp messenger

Group:          Development/Languages
License:        ASL 2.0
URL:            https://wiki.egi.eu/wiki/APEL/SSM
Source:         %{name}-%{version}-%{releasenumber}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

# Build requirement for non fedora-packager systems (CentOS).
%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
BuildRequires:  python-devel
%endif

Requires:       stomppy < 5.0.0, python-ldap < 3.4.0, python-setuptools, openssl
Requires(pre):  shadow-utils

%define ssmconf %_sysconfdir/apel

%description
The SSM is designed to give a reliable message transfer mechanism
using the STOMP protocol.  Messages are signed using the sender's
host certificate, and can optionally be encrypted.  This package
can act as either a sender or receiver.

The SSM is written in python.

%prep
%setup -q -n %{name}-%{version}-%{releasenumber}

%build

%install
rm -rf $RPM_BUILD_ROOT
# Create directories
mkdir -p %{buildroot}%{ssmconf}
mkdir -p %{buildroot}%{python_sitelib}
mkdir -p %{buildroot}%_bindir
mkdir -p %{buildroot}%{_sysconfdir}/logrotate.d
mkdir -p %{buildroot}%{_initrddir}
mkdir -p %{buildroot}%_defaultdocdir
# Directories for messages, logs, PID files
mkdir -p %{buildroot}%{_localstatedir}/spool/apel
mkdir -p %{buildroot}%{_localstatedir}/log/apel
mkdir -p %{buildroot}%{_localstatedir}/run/apel
# Scripts
cp -rp bin/sender.py %{buildroot}%_bindir/ssmsend
cp -rp bin/receiver.py %{buildroot}%_bindir/ssmreceive
cp -rp bin/apel-ssm %{buildroot}%{_initrddir}
# Copy SSM files
cp -rp conf/sender.cfg %{buildroot}%{ssmconf}
cp -rp conf/receiver.cfg %{buildroot}%{ssmconf}
cp -rp conf/dns %{buildroot}%{ssmconf}
cp -rp ssm %{buildroot}%{python_sitelib}

cp -rp scripts/apel-ssm.logrotate %{buildroot}%{_sysconfdir}/logrotate.d/apel-ssm

# Readme
cp -rp README.md %{buildroot}%_defaultdocdir/%{name}

%clean
rm -rf $RPM_BUILD_ROOT

%post
/sbin/chkconfig apel-ssm on

%preun
/sbin/service apel-ssm stop
/sbin/chkconfig apel-ssm off

%files
%defattr(-,root,root,-)
# SSM software itself
%attr(755,root,root) %_bindir/ssmsend
%attr(755,root,root) %_bindir/ssmreceive
%attr(755,root,root) %{_initrddir}/apel-ssm
%{python_sitelib}/ssm

# Directories for messages, logs, PID files
%dir %{_localstatedir}/spool/apel
%dir %{_localstatedir}/log/apel
%dir %{_localstatedir}/run/apel

%config(noreplace) %{ssmconf}/sender.cfg
%config(noreplace) %{ssmconf}/receiver.cfg
%config(noreplace) %{ssmconf}/dns

# logrotate
%config(noreplace) %{_sysconfdir}/logrotate.d/%{name}

%doc %_defaultdocdir/%{name}

%changelog
* Wed Feb 21 2024 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 3.4.0-1
 - Fixed compatability with newer versions of OpenSSL that only provide comma separated DNs.
 - Fixed Python 3 compatability (indirectly fixing EL8+ compatability) by performing explicit
   decoding. Note that this limits messages to ASCII as this is the current behaviour.
 - Added new build script that handles both RPM and DEB pacakging and later OSes.
 - Changed default config file values to bring in line with AMS usage.

* Mon Oct 09 2023 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 3.3.0-1
 - Added warning that BDII broker fetching will be deprecated in a future version.
 - Added non-zero exit status if sender or receiver crash.
 - Fixed SSM hanging if TCP connection drops by adding timeout.
 - Fixed directory queue system picking up sub-directories.
 - Fixed AMS messaging library dependency issue.
 - Fixed documentation for running a containerised receiver.
 - Fixed a few minor code issues.

* Thu Jun 29 2023 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 3.3.0-1
 - Added destination queue to the log during startup to aid troubleshooting.
 - Added check that the config file exists to allow for better error messages.
 - Changed dependencies to limit python-ldap below 3.4.0 and python-daemon below 2.3.0.
 - Changed rpmbuild config to use less OS-specific dependencies.
 - Fixed read timeouts leading to a crash.
 - Fixed command line arguments to allow a relative file path for the DNs file.
 - Removed the separate logging config file.
 - Removed python-daemon as a hard requirement as only needed for receivers.
 - Refactored a large amount of code for maintainability and security.

* Wed Apr 28 2021 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 3.2.1-1
 - Changed certificate and key comparison to allow both RSA and EC keys.
 - Corrected dependencies to include OpenSSL.

* Thu Mar 18 2021 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 3.2.0-1
 - Added logging of what certificate DNs/subjects are being used to facilitate
   troubleshooting.
 - Added stomp.py as .deb package dependency to avoid broken installations.
 - Refactored code to enable simpler external calls and better testing.

* Wed Dec 16 2020 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 3.1.1-1
 - Changed logging to reduce how verbose the logging of a 3rd-party module is.

* Tue Dec 01 2020 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 3.1.0-1
 - Enabled retries for all AMS communication methods to avoid timeouts from
   crashing SSM.

* Wed Sep 23 2020 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 3.0.0-1
 - As part of the migration to Python 3, this release removes support for
   Python 2.6.
 - The argo-ams-library is now an optional module, depending on whether AMS is
   used or not.
 - Fixed how the use_ssl config option is retrieved to avoid "referenced before
   assignment" errors leading to SSM failing to run.
 - Changes made to messaging loops to avoid high CPU usage.

* Tue Sep 03 2019 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.4.1-1
 - Fixed handling of OpenSSL errors so that messages that have been tampered
   with are now rejected.
 - Changed logging to remove excessive messages from a 3rd-party module used
   when sending via AMS.

* Thu Aug 01 2019 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.4.0-1
 - Added support for sending and receiving messages using the ARGO Messaging
   Service (AMS).
 - Added option to send messages from a directory without needing to conform to
   the file naming convention that the dirq module requires.
 - Fixed SSM hanging if certificate is not authorised with the broker. Now it
   will try other brokers if available and then correctly shut down.
 - Fixed an OpenSSL 1.1 syntax error by including missing argument to checkend.

* Wed Nov 28 2018 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.3.0-2
 - Updated build and test files only.

* Thu Aug 16 2018 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.3.0-1
 - Added support for stomp.py versions from 3.1.6 onwards which allows for
   builds on Ubuntu Trusty and should enable IPv6 support.
 - Added script for creating Ubuntu (.deb) builds.
 - Added script for creating Docker container builds.

* Mon May 14 2018 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.2.1-1
 - Added a check that the server certificate used for encryption hasn't expired
   so that a sending SSM won't start with an out of date server certificate.
 - Improved error handling for received messages so that more useful debugging
   information in obtained.

* Thu Nov 16 2017 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.2.0-1
 - Added a check that certificates have not expired before starting SSM.
 - SSL errors now propagated out properly and saved for received messages.
 - Trimmed down the number of log messages generated for receivers.
 - Added python-devel build requirement for non fedora-packager OSs (CentOS).

 * Tue Jan 12 2016 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.7-1
 - Added a delay when receiver is reconnecting to improve reliability.

 * Mon Mar 02 2014 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.6-1
 - Improved the log output for SSM receivers so that there are fewer trivial
   entries and so it's more useful in tracking messages on the filesystem.

 * Fri Nov 28 2014 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.5-1
 - (No changes from pre-release version.)

 * Fri Nov 28 2014 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.5-0.4.rc4
 - Corrected namespace of overridden variable (to enable SSL/TLS changes).

 * Fri Nov 28 2014 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.5-0.3.rc3
 - Removed python-ssl as a dependency as it can be option in some contexts.
 - Made it possible for old versions of stomp.py (3.0.3 and lower) to use
   SSL/TLS versions that aren't SSL 3.0.

 * Thu Nov 27 2014 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.5-0.2.rc2
 - Added a warning for old versions of stomp.py (3.0.3 and lower) that are
   limited to using SSL 3.0 for secure connections.

 * Tue Nov 25 2014 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.5-0.1.rc1
 - The highest version of SSL/TLS available is now used (previously only SSLv3).
 - Added python-ssl as a dependency (SL5/EL5 only).
 - Minor tweaks made to logging calls and the logging level of certain messages.

 * Fri Aug 08 2014 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.4-1
 - Corrected version number used in Python code.

 * Mon Jul 21 2014 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.3-1
 - (No changes from pre-release version.)

 * Thu Jul 17 2014 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.3-0.2.alpha1
 - RPM now enforces the use of stomppy < 4.0.0 as versions greater than this are
   currently incompatible with SSM.
 - Changes made to disconnection method which should prevent threading
   exceptions (mostly during shutdown).

 * Mon Jun 02 2014 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.2-0
 - The output of brokers.py has been improved so that it can be used to query
   the BDII for valid brokers.
 - The outgoing message directory will now be regularly cleared of empty
   directories and locked messages will be unlocked after five minutes.

 * Wed Oct 30 2013 Adrian Coveney <adrian.coveney@stfc.ac.uk> - 2.1.1-0
 - Reduced impact on message brokers of sending pings to refresh the connection.
 - Improved lost connection behaviour.

 * Tue Apr 16 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 2.1.0-0
 - Verify any certificate supplied for encrypting messages
   against the CA path
 - Receiver can check CRLs on certificates

 * Wed Feb 27 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 2.0.3-0
 - Add support for messages signed with quopri or base64
   content-transfer-encoding (for UNICORE).

 * Tue Feb 26 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 2.0.2-0
 - Fix SSL connection for receiver

 * Fri Feb 8 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 2.0.1-0
 - Fix crash when receiver sends ping message

 * Sat Jan 26 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 2.0.0-0
 - Fix SSL connection option
 - First release of SSM2

 * Fri Jan 25 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 0.0.4-0
 - Sensible defaults for release

 * Fri Jan 11 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 0.0.3-0
 - Changed rpm name to apel-ssm

 * Thu Jan 03 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 0.0.2-0
 - Fixed connection freeze

 * Fri Oct 02 2012 Will Rogers <will.rogers@stfc.ac.uk>  - 0.0.1-0
 - First tag
