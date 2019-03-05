#    Copyright 2019 UK Research and Innovation
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import unittest

import mock

from ssm import brokers


class Test(unittest.TestCase):

    def test_parse_stomp_url(self):

        wrong_url = 'this is not a correct url'
        try:
            brokers.parse_stomp_url(wrong_url)
            self.fail('Appeared to parse a fake URL.')
        except (IndexError, ValueError):
            # Expected exception
            pass

        http_url = 'http://not.a.stomp.url:8080'

        try:
            brokers.parse_stomp_url(http_url)
            self.fail('Parsed a URL which was not STOMP.')
        except ValueError:
            pass

        self.assertRaises(ValueError, brokers.parse_stomp_url,
                          'stomp://invalid.port.number:abc')

        stomp_url = 'stomp://stomp.cern.ch:6262'

        try:
            brokers.parse_stomp_url(stomp_url)
        except Exception:
            self.fail('Could not parse a valid stomp URL: %s' % stomp_url)

        stomp_ssl_url = 'stomp+ssl://stomp.cern.ch:61262'

        try:
            brokers.parse_stomp_url(stomp_ssl_url)
        except Exception:
            self.fail('Could not parse a valid stomp+ssl URL: %s' % stomp_url)

    def test_fetch_brokers(self):
        """Check the handling of responses from a mocked BDII."""
        bdii = 'ldap://no-bdii.utopia.ch:2170'
        network = 'PROD'

        sbg = brokers.StompBrokerGetter(bdii)

        # So that there are no external LDAP calls, mock out the LDAP seach.
        with mock.patch('ldap.ldapobject.SimpleLDAPObject.search_s',
                        side_effect=self._mocked_search):
            bs = sbg.get_broker_hosts_and_ports(brokers.STOMP_SERVICE, network)

        if len(bs) < 1:
            self.fail('No brokers found in the BDII.')

        host, port = bs[0]
        if not str(port).isdigit():
            self.fail('Got a non-integer port from fetch_brokers()')

        if '.' not in host:
            self.fail("Didn't get a hostname from fetch_brokers()")

        # Check that no brokers are returned from the TEST-NWOB network.
        test_network = 'TEST-NWOB'
        # So that there are no external LDAP calls, mock out the LDAP seach.
        with mock.patch('ldap.ldapobject.SimpleLDAPObject.search_s',
                        side_effect=self._mocked_search):
            test_bs = sbg.get_broker_hosts_and_ports(brokers.STOMP_SERVICE,
                                                     test_network)
        self.assertEqual(len(test_bs), 0, "Test brokers found in error.")

    def _mocked_search(*args, **kwargs):
        """Return values to mocked search call based on input."""

        if (
            '(&(objectClass=GlueService)(GlueServiceType=msg.broker.stomp))'
        ) in args:
            return [(
                'GlueServiceUniqueID=mq.cro-ngi.hr_msg.broker.stomp_3523291347'
                ',Mds-Vo-name=egee.srce.hr,Mds-Vo-name=local,o=grid',
                {'GlueServiceUniqueID':
                    ['mq.cro-ngi.hr_msg.broker.stomp_3523291347'],
                    'GlueServiceEndpoint': ['stomp://mq.cro-ngi.hr:6163/']}),
                    (
                'GlueServiceUniqueID=broker-prod1.argo.grnet.gr_msg.broker.sto'
                'mp_175215210,Mds-Vo-name=HG-06-EKT,Mds-Vo-name=local,o=grid',
                {'GlueServiceUniqueID':
                    ['broker-prod1.argo.grnet.gr_msg.broker.stomp_175215210'],
                    'GlueServiceEndpoint':
                    ['stomp://broker-prod1.argo.grnet.gr:6163/']}
            )]
        elif (
            '(&(GlueServiceDataKey=cluster)(GlueChunkKey=GlueServiceUniqueID='
            'mq.cro-ngi.hr_msg.broker.stomp_3523291347))'
        ) in args:
            return [(
                'GlueServiceDataKey=cluster,GlueServiceUniqueID=mq.cro-ngi.hr_'
                'msg.broker.stomp_3523291347,Mds-Vo-name=egee.srce.hr,Mds-Vo-n'
                'ame=local,o=grid', {'GlueServiceDataValue': ['PROD']}
            )]
        elif (
            '(&(GlueServiceDataKey=cluster)(GlueChunkKey=GlueServiceUniqueID='
            'broker-prod1.argo.grnet.gr_msg.broker.stomp_175215210))'
        ) in args:
            return [(
                'GlueServiceDataKey=cluster,GlueServiceUniqueID=broker-prod1.a'
                'rgo.grnet.gr_msg.broker.stomp_175215210,Mds-Vo-name=HG-06-EKT'
                ',Mds-Vo-name=local,o=grid', {'GlueServiceDataValue': ['PROD']}
            )]


if __name__ == '__main__':
    unittest.main()
