FROM rockylinux:9
LABEL org.opencontainers.image.authors="apel-admins@stfc.ac.uk" \
        org.opencontainers.image.title="APEL SSM" \
        org.opencontainers.image.description="Secure Stomp Messenger (SSM) is designed to simply send messages using the STOMP protocol." \
        org.opencontainers.image.source="https://github.com/apel/ssm" \
        org.opencontainers.image.licenses="Apache License, Version 2.0"

# Copy the SSM Git repository to /tmp/ssm
COPY . /tmp/ssm
# Then set /tmp/ssm as the working directory
WORKDIR /tmp/ssm

# Add the EPEL repo so we can get pip
RUN yum -y install epel-release && yum clean all
# Then get pip
RUN yum -y install python3-pip && yum clean all

# Install the system requirements of python-ldap
RUN yum -y install gcc python3-devel openldap-devel && yum clean all

# Install libffi, a requirement of openssl
RUN yum -y install libffi-devel && yum clean all

# Install the system requirements of ssm
RUN yum -y install openssl && yum clean all

# Install the python requirements of SSM
RUN pip install -r requirements-docker.txt
# Then install the SSM
RUN python3 setup.py install

# Set the working directory back to /
WORKDIR /
# Then delete the temporary copy of the SSM Git repository
# as there is no need for it after the image has been built.
RUN rm -rf /tmp/ssm
