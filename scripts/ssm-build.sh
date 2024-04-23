#!/bin/bash

# Apel-SSM Build Script 2.0: FPM edition
# Adapted from the Debian only build script, now with RPM!
# @Author: Nicholas Whyatt (RedProkofiev@github.com)

# Script runs well with FPM 1.14.2 on ruby 2.7.1, setuptools 51.3.3 on RHEL and Deb platforms

# Download ruby (if you're locked to 2.5, use RVM) and then run:
# sudo gem install fpm -v 1.14.2
# (may need to be run without the 'sudo')

# for RPM builds, you will also need:
# sudo yum install rpm-build rpmlint | sudo apt-get install rpm lintian
# ./ssm-build.sh (deb | rpm) <version> <iteration> <python_root_dir>
# e.g.
# ./ssm-build.sh deb 3.4.0 1 /usr/lib/python3.6
# If you're struggling finding the right version of Python to use, consider opening interpreter and:
# import site; site.getsitepackages()
# For SSM 3.4.0 and up.  Versions before that would technically work, but the changelog
# then was in a Debian format that doesn't parse and fails hard if you want to build RPM.

set -e

usage() {
    echo "Usage: $0 [options] (deb | rpm) <version> <iteration> <python_root_dir> "
    echo -e "Build script for Apel-SSM.\n"
    echo "  -h                    Displays help."
    echo "  -v                    Verbose FPM output."
    echo "  -s <source_dir>       Directory of source files.  Defaults to /debbuild/source or SOME RPM DIR."
    echo -e "  -b <build_dir>        Directory of build files.  Defaults to /debbuild/build or SOME RPM DIR.\n" 1>&2;
    exit 1;
}

# Bool flags to prevent automatic overwrite of input
SOURCE_ASSIGNED=0
BUILD_ASSIGNED=0

# Configurable options
while getopts ":hs:b:v" o; do
    case "${o}" in
        h)  echo "SSM Help"
            usage;
            ;;
        s)  s=${OPTARG}
            SOURCE_DIR=$s
            SOURCE_ASSIGNED=1
            ;;
        b)  b=${OPTARG}
            BUILD_DIR=$b
            BUILD_ASSIGNED=1
            ;;
        v)  VERBOSE="--verbose "
            ;;
        *)  usage;
            ;;
    esac
done
shift $((OPTIND-1))

# Check how any arguments there are
if [ "$#" -ne 4 ]; then
    echo "Expected 4 arguments, $# given."
    usage;
fi

PACK_TYPE=$1
VERSION=$2
ITERATION=$3
PYTHON_ROOT_DIR=$4 # i.e. /usr/lib/python3.6

# Alter library, build and source directories depending on the package
if [[ "$PACK_TYPE" = "deb" ]]; then
    LIB_EXTENSION="/dist-packages"
    if [[ "$SOURCE_ASSIGNED" = 0 ]]; then
        SOURCE_DIR=~/debbuild/source
    fi
    if [[ "$BUILD_ASSIGNED" = 0 ]]; then
        BUILD_DIR=~/debbuild/build
    fi
elif [[ "$PACK_TYPE" = "rpm" ]]; then
    LIB_EXTENSION="/site-packages"
    if [[ "$SOURCE_ASSIGNED" = 0 ]]; then
        SOURCE_DIR=~/rpmbuild/SOURCES
    fi
    if [[ "$BUILD_ASSIGNED" = 0 ]]; then
        BUILD_DIR=~/rpmbuild/BUILD
    fi
else # If package type is neither deb nor rpm, show an error message and exit
    echo "$0 currently only supports 'deb' and 'rpm' packages."
    usage;
fi

# Directory cleaning and repository management
# Create SSM and DEB dir (if not present)
mkdir -p "$SOURCE_DIR"
mkdir -p "$BUILD_DIR"

# Clean up any previous build
rm -rf "${SOURCE_DIR:?}"/*
rm -rf "${BUILD_DIR:?}"/*

# Get and extract the source
TAR_FILE=${VERSION}-${ITERATION}.tar.gz
TAR_URL=https://github.com/apel/ssm/archive/$TAR_FILE
wget --no-check-certificate "$TAR_URL" -O "$TAR_FILE"
tar xvf "$TAR_FILE" -C "$SOURCE_DIR"
rm -f "$TAR_FILE"

# Get supplied Python version
PY_VERSION="$(basename "$PYTHON_ROOT_DIR")"
PY_NUM=${PY_VERSION#python}
OS_EXTENSION="$(uname -r | grep -o 'el[7-9]' || echo '_all')"

# Universal FPM Call
FPM_CORE="fpm -s python \
    -t $PACK_TYPE \
    -n apel-ssm \
    -v $VERSION \
    --iteration $ITERATION \
    -m \"Apel Administrators <apel-admins@stfc.ac.uk>\" \
    --description \"Secure Stomp Messenger (SSM).\" \
    --no-auto-depends "

# Simple Python filter for version specific FPM
if [[ ${PY_NUM:0:1} == "3" ]]; then
    echo "Building $VERSION iteration $ITERATION for Python $PY_NUM as $PACK_TYPE."
    # python-stomp < 5.0.0 to python-stomp, python to python3/pip3
    # edited python-pip3 to python-pip
    # slight spelling inconsistencites betwixt OS's

    if [[ "$PACK_TYPE" = "deb" ]]; then
        FPM_PYTHON="--depends python3 \
        --depends python3-pip \
        --depends 'python3-stomp' \
        --depends python3-ldap \
        --depends libssl-dev \
        --depends libsasl2-dev \
        --depends openssl "

    # Currently builds for el8
    elif [[ "$PACK_TYPE" = "rpm" ]]; then
        FPM_PYTHON="--depends python3 \
        --depends python3-stomppy \
        --depends python3-pip \
        --depends python3-ldap \
        --depends openssl \
        --depends openssl-devel "
    fi

elif [[ ${PY_NUM:0:1} == "2" ]]; then
    echo "Building $VERSION iteration $ITERATION for Python $PY_NUM as $PACK_TYPE."

    if [[ "$PACK_TYPE" = "deb" ]]; then
        FPM_PYTHON="--depends python2.7 \
        --depends python-pip \
        --depends 'python-stomp < 5.0.0' \
        --depends python-ldap \
        --depends libssl-dev \
        --depends libsasl2-dev \
        --depends openssl "

    # el7 and below, due to yum package versions
    elif [[ "$PACK_TYPE" = "rpm" ]]; then
        FPM_PYTHON="--depends python2 \
        --depends python2-pip \
        --depends stomppy \
        --depends python-ldap \
        --depends openssl \
        --depends openssl-devel "
    fi
fi

# python-bin must always be specified in modern linux
PACKAGE_VERSION="--$PACK_TYPE-changelog $SOURCE_DIR/ssm-$VERSION-$ITERATION/CHANGELOG \
    --$PACK_TYPE-dist $OS_EXTENSION \
    --python-bin /usr/bin/$PY_VERSION \
    --python-install-bin /usr/bin \
    --python-install-lib $PYTHON_ROOT_DIR$LIB_EXTENSION \
    --exclude *.pyc \
    --package $BUILD_DIR \
    $SOURCE_DIR/ssm-$VERSION-$ITERATION/setup.py"

# Construct and evaluate the primary FPM call
BUILD_PACKAGE_COMMAND=${FPM_CORE}${FPM_PYTHON}${VERBOSE}${PACKAGE_VERSION}
eval "$BUILD_PACKAGE_COMMAND"

echo "== Generating pleaserun package =="

# When installed, use pleaserun to perform system specific service setup
fpm -s pleaserun -t "$PACK_TYPE" \
-n apel-ssm-service \
-v "$VERSION" \
--iteration "$ITERATION" \
--"$PACK_TYPE"-dist "$OS_EXTENSION" \
-m "Apel Administrators <apel-admins@stfc.ac.uk>" \
--description "Secure Stomp Messenger (SSM) Service Daemon files." \
--architecture all \
--no-auto-depends \
--depends apel-ssm \
--package "$BUILD_DIR" \
/usr/bin/ssmreceive

echo "Possible Issues to Fix:"
if [ "$OS_EXTENSION" == "_all" ]
then
    # Check the resultant debs for 'lint'
    TAG="$VERSION-$ITERATION"
    lintian "$BUILD_DIR"/apel-ssm_"${TAG}"_all.deb
    lintian "$BUILD_DIR"/apel-ssm-service_"${TAG}"_all.deb
else
    # Check for errors in SPEC and built packages
    # For instance; Given $(dirname /root/rpmb/rpmbuild/source) will output "/root/rpmb/rpmbuild".
    rpmlint "$(dirname "$SOURCE_DIR")"
fi
