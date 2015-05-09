#!/usr/bin/env python

'''Part 1 of ETL app.

   Tails a log file. Uses regex to EXTRACT events and errors.
   TRANSFORMS before sending a post request to Flask app to LOAD.

   @params: filename, name of log file to tail

   @params: post_path, http for post request
   '''

import os
import json
import re
import time
import requests
import sys
import subprocess
from subprocess import Popen, PIPE
from optparse import OptionParser

f = None

def get_next_line():
    '''Grabs next line of log file'''
    global f
    while True:
        line = f.readline()
        if line:
            # remove trailing \n
            return line[:-1]
        time.sleep(0.1)

def get_block(data):
    '''Returns block of logfile lines containing stack trace,
    and the lines following the stack, to restart the bank of six lines
    '''
    while True:
        line = get_next_line()
        if line:
            #detect if line is part of a stack
            if re.match('^(\s{4}\w+)', line) or re.search('(----)', line):
                data.append(line)
            else:
                return data, line

def get_error_type(data):
    '''Classifies error type.
    Presence of '^' indicates an uncaught exception'''
    text = []
    for line in data:
        text.append(line.split())

    if ['^'] in text:
        return "uncaught"
    else:
        return "caught"


def get_message(data):
    '''Retrieves error message if present'''
    # identify line number of "Error:message"
    pos = 0
    for i, line in enumerate(data):
        if re.search('Error', line):
            pos = i
            break

    # if Error:message is found
    if pos != 0:
        mess = data[pos].split(":")

        # determine if message is blank
        if len(mess) > 1:
            return mess
        else:
            return ["Unknown", "Unknown"]

    # format different from Error:message
    else:
        # likely position for message
        if data[-2]:
            mess = data[-2].split(":")

            if len(mess) > 1:
                return mess
            else:
                return ["Unknown", "Unknown"]

        # if message is still not found
        else:
            return ["Unknown", "Unknown"]

def get_origin(data):
    '''Retrieves origin of error if present'''
    # uncaught exception states module name 2 lines before '^'
    pos = 0
    for i, line in enumerate(data):
        if '^' in line:
            pos = i - 2
            break

    # if present will be module:line number
    if re.search('(:)', data[pos]):
        return data[pos].strip().split(":")
    else:
        return ["Unknown", "Unknown"]

def find_stack(data):
    '''Trim lines before stack'''
    pos = 0
    for i, line in enumerate(data):
        if re.match('^(\s{4}\w+)', line):
            pos = i
            break

    return data[pos:]

# extract error from log file
def get_error(bank, post_path, filename, hostname):
    '''Extracts error from log file
    Returns line after error to add to bank of six lines'''
    # establish common info
    file_string = filename.split("/")
    phile = file_string[-1]
    header = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    data, spill_over = get_block(bank)

    if get_error_type(bank) == 'uncaught':

        mess = get_message(bank)
        origin = get_origin(bank)

        # construct error data
        info = {}
        info['type'] = mess[0]
        info['message'] = " ".join(mess[1:])
        info['origin'] = origin[0]
        info['line_number'] = origin[1]
        info['stack'] = find_stack(data)
        info['host_name'] = hostname
        info['filename'] = phile

        # send post request
        earl = "%s/uncaught" % (post_path)
        payload = json.dumps(info)
        r = requests.post(earl, data=payload, headers=header)
        sys.stdout.write('.')
        sys.stdout.flush()
    else:

        mess = get_message(bank)

        info = {}
        info['type'] = mess[0]
        info['message'] = " ".join(mess[1:])
        info['stack'] = find_stack(data)
        info['host_name'] = hostname
        info['filename'] = phile

        earl = "%s/caught" % (post_path)
        payload = json.dumps(info)
        r = requests.post(earl, data=payload, headers=header)
        sys.stdout.write('.')
        sys.stdout.flush()
    return spill_over

def send_events(events, post_path):
    '''Sends batch events post request'''
    header = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    earl = "%s/events_many" % (post_path)
    payload = json.dumps(events)
    r = requests.post(earl, data=payload, headers=header)
    return []

def get_event(line, filename, hostname):
    '''Extracts and transforms event from log file'''
    # extract event info from string and 
    # add the logfile name and server info to event structure
    # before: 'Event: ["add something","info","2013-07-02T19:47:41.585Z",
    #                  "backend-web",{"id":"whatever"}]'
    # after: '["logfile.log", "hostname","add something","info",
    #          "2013-07-02T19:47:41.585Z","backend-web",{"id":"whatever"}]
    file_string = filename.split("/")
    phile = file_string[-1]
    event = '["%s","%s",' %(phile, hostname) + line[8:]
    return event

def get_hostname():
    '''Gets server info (compatible with python < 2.7)'''
    host = subprocess.Popen('hostname', stdout=PIPE)
    # remove trailing \n
    hostname = host.communicate()[0][:-1]

    return hostname

def main(filename, post_path):
    '''Extracts and transforms errors and events.
    Sends post request to Flask app'''

    global f
    f = open(filename)
    hostname = get_hostname()
    f.seek(0, os.SEEK_END)

    # keep a rolling block of six lines at all times
    # actually detects the four whitespaces that start a stack trace
    # so we need to keep the previous six lines to extract the
    # error type and source of error 
    # example:
    #
    #source of error: module.js:103
    #                 if (!process.listeners('uncaughtException').length) throw e;
    #                                    ^
    #
    #error message:   Error: Carly this is uncaught
    #detected line:       at Object.<anonymous> (/home/ubuntu/product/index.js:48:8)
    
    bank = ["one", "two", "three", "four", "five", "six"]
    events = []
    while True:
        line = get_next_line()
        bank.pop(0)
        bank.append(line)

        # detect 4 white spaces (see note above)
        if re.match('^(\s{4}\w+)', line):
            spill_over = get_error(bank, post_path, filename, hostname)
            # reset to avoid error overlap
            bank = ["one", "two", "three", "four", "five", spill_over]

        # detect event [see note 2]
        elif re.match('^Event:', line):
            event = get_event(line, filename, hostname)
            events.append(event)
        # send events in batches of at least 20
        if len(events) >= 20:
            events = send_events(events, post_path)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-f', '--filename', help='logfile_name')
    parser.add_option('-p', '--post_path', help='post request url,\
                      (set to http://localhost:7000 for dev mode)')
    options, args = parser.parse_args()
    main(options.filename, options.post_path)
