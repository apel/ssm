#!/bin/bash

# Apel-SSM Build Script 2.0: FPM edition
# Adapted from the Debian only build script, now with RPM!
# @Author: Nicholas Whyatt (RedProkofiev@github.com)

set -e

usage() { 
    echo "Usage: $0 (deb | rpm) <version> <iteration> <python_root_dir> [options]"
    echo -e "Build script for Apel-SSM.\n"
    echo "  -h                    Displays help."
    echo "  -s <source_dir>       Directory of source files.  Defaults to /debbuild/source or SOME RPM DIR." 
    echo -e "  -b <build_dir>        Directory of build files.  Defaults to /debbuild/build or SOME RPM DIR.\n" 1>&2;
    exit 1; 
}

# cheap python hack!
# if ! python3 -c 'import sys; assert sys.version_info >= (3,6)' > /dev/null; then
#     export PYTHON_VERSION=`python -c 'import sys; version=sys.version_info[:3]; print("{0}.{1}".format(*version))'
# elif ! python2 -c 'import sys; assert sys.version_info >= (3,6)' > /dev/null; then

SOURCE_ASSIGNED=0
BUILD_ASSIGNED=0

# Configurable options
while getopts ":hs:b:" o; do
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

# TODO: Replace rpm directories with their sensible equivalents
# It ain't pretty, but it is readable and it gets the job done
# LIB_EXTENSION is the install dir for python lib files, and is system dependent
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
        SOURCE_DIR=~/something/rpm
    fi
    if [[ "$BUILD_ASSIGNED" = 0 ]]; then
        BUILD_DIR=~/somethingalso/rpm
    fi
else # If package type is neither deb nor rpm, show an error message and exit
    echo "$0 currently only supports 'deb' and 'rpm' packages."
    usage;
fi

# Testing
echo $LIB_EXTENSION
echo $SOURCE_DIR
echo $BUILD_DIR

# # Create SSM and DEB dir (if not present)
# mkdir -p $SOURCE_DIR
# mkdir -p $BUILD_DIR

# # Clean up any previous build
# rm -rf $SOURCE_DIR/*
# rm -rf $BUILD_DIR/*

# # Get and extract the source
# TAR_FILE=${VERSION}-${ITERATION}.tar.gz
# TAR_URL=https://github.com/apel/ssm/archive/$TAR_FILE
# wget --no-check-certificate $TAR_URL -O $TAR_FILE
# tar xvf $TAR_FILE -C $SOURCE_DIR
# rm -f $TAR_FILE

# Get specific python version
# Main distinction is 2 vs 3 but also check for 3.5 or under or under 2.7

PY_VERSION=$(basename $PYTHON_ROOT_DIR)
PY_NUM=${PY_VERSION#python}
echo $PY_NUM

# One fpm call for python 2, one for python 3
# Check for each based on minimum versioning
# May have to vary by debian and RPM too :/
# add in commands?

# Create two sections, tack them together, render with eval command
# Section 1: Python Version specific
# Section 2: RPM or DEB?
# Eval

if (( ${PY_NUM:0:1} == 2 )) ; then
    if (( ${PY_NUM:2:3} < 7 )) ; then # or version is later than 4.0.0
        echo "Python version is insufficient, you supplied $PY_NUM when you need 2.7.  Python 2 will be removed in 4.0.0."
        usage;
    fi
    # py2 FPM call CURRENTLY DEBIAN
    # adapt for RPM and for generalism
    # eval 

    echo "Building $VERSION iteration $ITERATION for Python $PY_NUM as $PACK_TYPE."


    fpm -s python -t deb \
    -n apel-ssm \
    -v $VERSION \
    --iteration $ITERATION \
    -m "Apel Administrators <apel-admins@stfc.ac.uk>" \
    --description "Secure Stomp Messenger (SSM)." \
    --no-auto-depends \
    --depends python2.7 \
    --depends python-pip \
    --depends 'python-stomp < 5.0.0' \
    --depends python-ldap \
    --depends libssl-dev \
    --depends libsasl2-dev \
    --depends openssl \
    --deb-changelog $SOURCE_DIR/ssm-$TAG/CHANGELOG \
    --python-install-bin /usr/bin \
    --python-install-lib $PYTHON_INSTALL_LIB \
    --exclude *.pyc \
    --package $BUILD_DIR \
    $SOURCE_DIR/ssm-$TAG/setup.py

elif (( ${PY_NUM:0:1} == 3 )) ; then
    if (( ${PY_NUM:2:3} < 6 )) ; then
        echo "Python version is insufficient, you supplied $PY_NUM when you need above 3.5."
        usage;
    fi
    #py3 fpm call
    echo "Building $VERSION iteration $ITERATION for Python $PY_NUM as $PACK_TYPE."

fi

# Create pleaserun command
# Section 1: RPM or DEB ?
# Don't need to eval, just change deb

eval build_package

fpm -s pleaserun -t $PACK_TYPE \
    -n apel-ssm-service \
    -v $VERSION \
    --iteration $ITERATION \
    -m "Apel Administrators <apel-admins@stfc.ac.uk>" \
    --description "Secure Stomp Messenger (SSM) Service Daemon files." \
    --architecture all \
    --no-auto-depends \
    --depends apel-ssm \
    --package $BUILD_DIR \
    /usr/bin/ssmreceive
