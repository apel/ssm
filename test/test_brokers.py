'''
   Copyright (C) 2012 STFC

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
'''

from ssm import brokers

import unittest

class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def test_parse_stomp_url(self):
        
        wrong_url = "this is not a correct url"
        try:
            brokers.parse_stomp_url(wrong_url)
            self.fail("Appeared to parse a fake URL.")
        except (IndexError, ValueError):
            # Expected exception
            pass
            
        http_url = "http://not.a.stomp.url:8080"
        
        try:
            brokers.parse_stomp_url(http_url)
            self.fail("Parsed a URL which was not STOMP.")
        except ValueError:
            pass
        
        stomp_url = "stomp://stomp.cern.ch:6262"
        
        try:
            brokers.parse_stomp_url(stomp_url)
        except:
            self.fail("Could not parse a valid stomp URL: %s" % stomp_url)        
        

        stomp_ssl_url = "stomp+ssl://stomp.cern.ch:61262"
        
        try:
            brokers.parse_stomp_url(stomp_ssl_url)
        except:
            self.fail("Could not parse a valid stomp+ssl URL: %s" % stomp_url)        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()