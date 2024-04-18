FROM rockylinux:9
MAINTAINER APEL Administrators <apel-admins@stfc.ac.uk>

# Copy the SSM Git repository to /tmp/ssm
COPY . /tmp/ssm
# Then set /tmp/ssm as the working directory
WORKDIR /tmp/ssm

# Add the EPEL repo so we can get pip
RUN yum -y install epel-release && yum clean all
# Then get pip
RUN yum -y install python-pip && yum clean all

# Install the system requirements of python-ldap
RUN yum -y install gcc python-devel openldap-devel && yum clean all

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
