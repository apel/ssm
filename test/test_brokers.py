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

from ssm import brokers

import unittest


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
        '''
        Requires an internet connection to get information from the BDII.
        Could fail if the BDII is down. This isn't very unit-test-like.
        '''
        bdii = 'ldap://lcg-bdii.cern.ch:2170'
        network = 'PROD'

        sbg = brokers.StompBrokerGetter(bdii)

        bs = sbg.get_broker_hosts_and_ports(brokers.STOMP_SERVICE, network)

        if len(bs) < 1:
            self.fail('No brokers found in the BDII.')

        host, port = bs[0]
        if not str(port).isdigit():
            self.fail('Got a non-integer port from fetch_brokers()')

        if '.' not in host:
            self.fail("Didn't get a hostname from fetch_brokers()")


if __name__ == '__main__':
    unittest.main()
