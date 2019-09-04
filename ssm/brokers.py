'''
   Copyright (C) 2012 STFC.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

   @author: Will Rogers

Class to interact with a BDII LDAP server to retrieve information about
the stomp brokers specified in a network.
'''
import ldap
import logging

log = logging.getLogger(__name__)

# Constants used for specific LDAP queries
STOMP_SERVICE = 'msg.broker.stomp'
STOMP_SSL_SERVICE = 'msg.broker.stomp-ssl'

STOMP_PREFIX = 'stomp'
STOMP_SSL_PREFIX = 'stomp+ssl'

class StompBrokerGetter(object):
    '''
    Given the URL of a BDII, searches for all the STOMP
    brokers listed that are part of the specified network.
    '''

    def __init__(self, bdii_url):
        '''
        Set up the LDAP connection and strings which are re-used.
        '''
        # Set up the LDAP connection
        log.debug('Connecting to %s...', bdii_url)
        self._ldap_conn = ldap.initialize(bdii_url)

        self._base_dn = 'o=grid'
        self._service_id_key = 'GlueServiceUniqueID'
        self._endpoint_key  = 'GlueServiceEndpoint'
        self._service_data_value_key = 'GlueServiceDataValue'

    def get_broker_urls(self, service_type, network):
        '''
        Gets the list of all the stomp brokers in the BDII, then
        checks them to see if they are part of the network.  The network
        is supplied as a string.
        Returns a list of URLs.
        '''
        prod_broker_urls = []

        broker_details = self._get_broker_details(service_type)

        for broker_id, broker_url in broker_details:
            if self._broker_in_network(broker_id, network):
                prod_broker_urls.append(broker_url)

        return prod_broker_urls

    def get_broker_hosts_and_ports(self, service_type, network):
        '''
        Gets the list of all the stomp brokers in the BDII, then
        checks them to see if they are part of the network. The network
        is supplied as a string.
        Returns a list of (host, port) tuples.
        '''
        urls = self.get_broker_urls(service_type, network)
        hosts_and_ports = []
        for url in urls:
            hosts_and_ports.append(parse_stomp_url(url))
        return hosts_and_ports

    def _get_broker_details(self, service_type):
        '''
        Searches the BDII for all STOMP message brokers.  Returns a list of
        tuples: (<GlueServiceUniqueID>, <URL>).
        '''
        broker_details = []

        ldap_filter = '(&(objectClass=GlueService)(GlueServiceType=%s))' % service_type
        attrs = [self._service_id_key, self._endpoint_key]

        brokers = self._ldap_conn.search_s(self._base_dn, ldap.SCOPE_SUBTREE, ldap_filter, attrs)

        for unused_dn, attrs in brokers:
            details = attrs[self._service_id_key][0], attrs[self._endpoint_key][0]
            broker_details.append(details)

        return broker_details

    def _broker_in_network(self, broker_id, network):
        '''
        Given a GlueServiceUniqueID for a message broker, check that it is
        part of the specified network.
        '''
        ldap_filter = '(&(GlueServiceDataKey=cluster)(GlueChunkKey=GlueServiceUniqueID=%s))' \
            % broker_id
        attrs = [self._service_data_value_key]
        results = self._ldap_conn.search_s(self._base_dn, ldap.SCOPE_SUBTREE, ldap_filter, attrs)

        try:
            unused_dn, attrs2 = results[0]
            return network in attrs2[self._service_data_value_key]
        except IndexError: # no results from the query
            return False

def parse_stomp_url(stomp_url):
    '''
    Given a URL of the form stomp://stomp.cern.ch:6262/,
    return a tuple containing (stomp.cern.ch, 6262).
    '''
    parts = stomp_url.split(':')

    protocols = [STOMP_PREFIX, STOMP_SSL_PREFIX]
    if not parts[0].lower() in protocols:
        raise ValueError("URL %s does not begin 'stomp:'." % stomp_url)

    host = parts[1].strip('/')
    port = parts[2].strip('/')
    if not port.isdigit():
        raise ValueError('URL %s does not have an integer as its third part.')

    return host, int(port)


if __name__ == '__main__':
    # BDII URL
    BDII = 'ldap://lcg-bdii.cern.ch:2170'
    BG = StompBrokerGetter(BDII)

    def print_brokers(text, service, network):
        brokers = BG.get_broker_hosts_and_ports(service, network)
        # Print section heading
        print('==', text, '==')
        # Print brokers in form 'host:port'
        for broker in brokers:
            print('%s:%i' % (broker[0], broker[1]))
        # Leave space between sections
        print()

    print_brokers('SSL production brokers', STOMP_SSL_SERVICE, 'PROD')
    print_brokers('Production brokers', STOMP_SERVICE, 'PROD')
    print_brokers('SSL test brokers', STOMP_SSL_SERVICE, 'TEST-NWOB')
    print_brokers('Test brokers', STOMP_SERVICE, 'TEST-NWOB')
