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
'''

import logging
import sys

__version__ = (0, 0, 1)

def set_up_logging(logfile, lvl, console):
    
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(filename=logfile, format=fmt, level=lvl)
    
    if console:
        log = logging.getLogger()
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(lvl)
        formatter = logging.Formatter(fmt)
        ch.setFormatter(formatter)
        log.addHandler(ch)
    
    