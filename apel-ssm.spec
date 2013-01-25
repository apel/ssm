# Conditionally define python_sitelib
%if ! (0%{?fedora} > 12 || 0%{?rhel} > 5)
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif

Name:           apel-ssm
Version:        0.0.4
Release:        0%{?dist}
Summary:        Secure stomp messenger

Group:          Development/Languages
License:        ASL 2.0
URL:            https://wiki.egi.eu/wiki/APEL/SSM
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

Requires:       stomppy, python-daemon, python-dirq, python-ldap
Requires(pre):  shadow-utils

%define ssmconf %_sysconfdir/apel

%description
The SSM is designed to give a reliable message transfer mechanism
using the STOMP protocol.  Messages are signed using the sender's
host certificate, and can optionally be encrypted.  This package
can act as either a sender or receiver.

The SSM is written in python.

%prep
%setup -q -n %{name}-%{version}

%install
rm -rf $RPM_BUILD_ROOT
# Create directories
mkdir -p %{buildroot}%{ssmconf}
mkdir -p %{buildroot}%{python_sitelib}
mkdir -p %{buildroot}%_bindir
mkdir -p %{buildroot}/etc/logrotate.d
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
cp -rp conf/ssm.logrotate %{buildroot}%_sysconfdir/logrotate.d/%{name}
# Readme
cp -rp README %{buildroot}%_defaultdocdir/%{name}

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
# logrotate

# Directories for messages, logs, PID files
%dir %{_localstatedir}/spool/apel
%dir %{_localstatedir}/log/apel
%dir %{_localstatedir}/run/apel

%config(noreplace) %{ssmconf}/sender.cfg
%config(noreplace) %{ssmconf}/receiver.cfg
%config(noreplace) %{ssmconf}/dns
%config(noreplace) /etc/logrotate.d/%{name}

%doc %_defaultdocdir/%{name}

%changelog
 * Fri Jan 25 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 0.0.4-0
 - Sensible defaults for release

 * Fri Jan 11 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 0.0.3-0
 - Changed rpm name to apel-ssm

 * Thu Jan 03 2013 Will Rogers <will.rogers@stfc.ac.uk>  - 0.0.2-0
 - Fixed connection freeze
 
 * Fri Oct 02 2012 Will Rogers <will.rogers@stfc.ac.uk>  - 0.0.1-0
 - First release
