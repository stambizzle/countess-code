'''Flask App to process post requests from logreader.py
and display events.'''

import os
import pymongo
from flask import Flask, request, json, render_template
from flask_sslify import SSLify

import loggit

app = Flask(__name__)
app.config['DEBUG'] = False
sslify = SSLify(app)

conn = pymongo.Connection('connection_string')

@app.route("/")
def greet():
    '''Home page'''
    return render_template('home_page')

@app.route("/uncaught", methods=['POST'])
def uncaught():
    '''Process uncaught exception'''
    loggit.catch_errors(request.json, conn)
    return "ok"

@app.route("/caught", methods=['POST'])
def caught():
    '''Process caught exception'''
    loggit.catch_errors(request.json, conn)
    return "ok"

@app.route('/events_many', methods=['POST'])
def process_array():
    '''Process a batch of events'''
    loggit.process_array(request.json, conn)
    return "ok"

@app.route('/events', methods=['POST'])
def process_event():
    '''Process a single event'''
    loggit.catch_events(json.loads(request.json), conn)
    return "ok"

@app.route('/events', methods=['GET'])
def show_events():
    '''Show recent events'''
    return render_template('multiple_events_template')

@app.route('/event/<path:event_id>')
def show_event(event_id):
    '''Show details of a specific event (function details removed)'''
    return render_template('single_event_template')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 0000))
    app.run(host='0.0.0.0', port=port)
