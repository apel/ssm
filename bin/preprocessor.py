#!/usr/bin/env python

#   Copyright (C) 2012 STFC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Script to run a sending SSM."""

from __future__ import print_function

import ssm.agents
from ssm import __version__, LOG_BREAK
import os
import logging
from optparse import OptionParser
from dirq.QueueSimple import QueueSimple
from ssm.message_directory import MessageDirectory
import re

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser


def _get_path_to_outq(cp):
    try: 
        qpath = cp.get('messaging', 'path')
        print(qpath)
    except:
        raise ValueError('Cannot retrieve path to outq.')
    return qpath


def _get_path_type(cp, log):
    try:
        path_type = cp.get('messaging', 'path_type')
    except ConfigParser.NoOptionError:
        log.info('No path type defined, assuming dirq.')
        print('No path type defined')
        path_type = 'dirq'
    return path_type


def _get_queue(qpath, path_type):

    for dirpath, dirnames, files in os.walk(qpath):
        dirs_at_path = dirnames
        files_at_path = files
        path_examined = qpath
        break

    if path_type == 'dirq':
        if QueueSimple is None:
            raise ImportError('Dirq path_type requested but'
                              'dirq module not found.')

        if (len(dirs_at_path) == 0 or 
           (len(dirs_at_path) == 1 and dirs_at_path[0] == 'combined_queue')):
            raise ValueError("Provided path_type was dirq but no "
                             "directory found at path. Should "
                             "path_type be 'directory'?")

        outq = QueueSimple(qpath)

    elif path_type == 'directory':
        if len(dirs_at_path) > 0:
            raise ValueError("Provided path_type was directory but an "
                             "unexpected directory is present at path, "
                             "as well as files. Should path_type be 'dirq'?")

        outq = MessageDirectory(qpath)

    else:
        raise ValueError('Unsupported path_type variable.')

    return outq


def _header_matches_regex(header):
    regex_expr_header = re.compile(r'^APEL(?:-[a-z]+)+-message: v[0-9].[0-9]$')
    return regex_expr_header.match(header)


def _first_time_executing_code(previous_header):
    if previous_header == None:
        return True
    else:
        return False


def _add_to_queue(msg, queue_combined_msgs, originally_a_string):
    if originally_a_string:
        queue_combined_msgs.add(msg)
    else:    
        msg_in_bytes = str.encode(msg)
        queue_combined_msgs.add(msg_in_bytes)
    return 



def _create_new_queue(new_path, path_type):

    if path_type == 'dirq':
        newq = QueueSimple(new_path)

    elif path_type == 'directory':
        if not os.path.exists(new_path):
            os.makedirs(new_path)
        newq = MessageDirectory(new_path)

    else:
        raise ValueError('Unsupported path_type variable.')

    return newq


def _determine_what_to_iterate(outq, path_type):

    if path_type == 'dirq':
        structure_to_iterate = outq
    elif path_type == 'directory':
        structure_to_iterate = outq._get_messages()
    else:
        raise ValueError('Unsupported path_type variable.')

    return structure_to_iterate





def create_queue_combined_msgs(cp, log):

    previous_header = None
    n_msg_combined = 0
    n_max_msg_combined = 500
    qpath = _get_path_to_outq(cp)
    combined_queue_path = os.path.join(qpath, 'combined_queue')
    path_type = _get_path_type(cp, log)
    outq = _get_queue(qpath, path_type) 
    structure_to_iterate = _determine_what_to_iterate(outq, path_type)
    queue_combined_msgs = _create_new_queue(combined_queue_path, path_type)

    for msgid in structure_to_iterate:
        if not outq.lock(msgid):
            log.warning('Message was locked. %s will not be read.', msgid)
            continue

        text = outq.get(msgid)
        originally_a_string = True
        try:
            text = text.decode()
            originally_a_string = False
        except (UnicodeDecodeError, AttributeError):
            pass

        splitted_content = text.split('\n')
        header = splitted_content[0]
        contents_minus_header = splitted_content[1:]

        if _header_matches_regex(header):
            if header == previous_header and n_msg_combined < n_max_msg_combined:
                combined_msgs = combined_msgs + '\n' + '\n'.join(contents_minus_header)
                n_msg_combined += 1
            else:
                if not _first_time_executing_code(previous_header):
                    _add_to_queue(combined_msgs, queue_combined_msgs, originally_a_string)
                
                combined_msgs = text
                previous_header = header
                n_msg_combined = 1
            
        outq.remove(msgid)

    
    _add_to_queue(combined_msgs, queue_combined_msgs, originally_a_string)        

    try:
        outq.purge()
    except OSError as e:
        log.warning('OSError raised while purging message queue: %s', e)

    return combined_queue_path

