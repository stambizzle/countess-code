'''Log events and errors.'''

import json
import datetime

def catch_errors(data, conn):
    '''Log events through the route (/errors).
    Depends on specific structure sent from cloudlog_reader.py'''

    # these are upper level keys that shouls be present for every every event
    info = {}
    info['date'] = datetime.datetime.utcnow() #errors do not include timestamp
    info['filename'] = data['filename']
    info['host_name'] = data['host_name']
    if data.has_key('line_number'):
        info['name'] = 'uncaught exception'
        info['type'] = 'error'
    else:
        info['name'] = 'caught exception'
        info['type'] = 'warn'

    # these are keys specific to errors
    keep = ['message', 'stack', 'type', 'origin', 'line_number']
    info['data'] = {}
    for key, value in data.items():
        if key in keep:
            info['data'][key] = value
    log_event(info, conn)

def catch_events(event, conn):
    '''Log events through the route (/events).
    Depends on specific structure from cloudlog_reader.py'''
    info = {}

    # upper level keys
    info['filename'] = event[0]
    info['host_name'] = event[1]
    info['name'] = event[2]
    info['type'] = event[3]
    info['date'] = event[4]

    #event specific info
    info['data'] = event[5]

    log_event(info, conn)

def process_array(events, conn):
    '''Process events sent as an array (buffering)'''
    for event in events:
        print event
        catch_events(json.loads(event), conn)

def log_event(info, conn):
    '''Save event to database and send any necessary alerts'''
    database = conn['yourdatabasename']
    database.new_events.save(info)

    #here is where you would send to IRC or use github API to create issue
