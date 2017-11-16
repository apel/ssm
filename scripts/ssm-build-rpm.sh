#!/bin/bash

# Execute the following as root to install build tools and create a build user:
# yum install fedora-packager
# useradd -m rpmb
# usermod -a -G mock rpmb

# Then swtich to the rpmb user (su - rpmb) and run this file, altering version.

rpmdev-setuptree

RPMDIR=/home/rpmb/rpmbuild
VERSION=2.2.0-1
SSMDIR=apel-ssm-$VERSION

# Remove old sources and RPMS
rm -f $RPMDIR/SPECS/*
rm -f $RPMDIR/SOURCES/*
rm -f $RPMDIR/SRPMS/*
rm -f $RPMDIR/RPMS/noarch/*

wget --no-check-certificate https://github.com/apel/ssm/archive/$VERSION.tar.gz -O $VERSION

tar xzvf $VERSION
rm $VERSION

mv ssm-$VERSION $SSMDIR

tar czvf $SSMDIR.tar.gz $SSMDIR
cp $SSMDIR.tar.gz $RPMDIR/SOURCES
cp $SSMDIR/apel-ssm.spec $RPMDIR/SPECS

rpmbuild -ba $RPMDIR/SPECS/apel-ssm.spec

# Clean up (note there are both leading and trailing asterisks)
rm -rf *ssm-$VERSION*
