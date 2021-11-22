#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from typing import Dict
import flask
from flask import Flask, request, redirect
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

from gevent.greenlet import Greenlet

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True



class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()  

gevents : Dict[Greenlet] = dict()



class SocketListenerThing:

    def __init__(self, socket: Sockets):
        
        self.socket :Sockets = socket 
    
    def __call__(self, entity : str, data : dict):
        #do stuff here
        global gevents
        if self.socket.closed:
            myWorld.listeners.remove(self)
            if self.socket in gevents:
                gevent.kill(gevents[self.socket])
            print('socket is closed, remove lisntener and killing gevent')
            return
        print('sent')
        self.socket.send(json.dumps({entity:data}))
     
    

        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return redirect("/static/index.html", code=301)

def read_ws(ws :Sockets):
    '''A greenlet function that reads from the websocket and updates the world'''
    try:
        while True:
            msg = ws.receive()
            print(f'bruh {msg}')
            if msg:
                packet :dict = json.loads(msg)
                
                data : dict
                for entity, data in packet.items():
                    for key, val in data.items():
                        myWorld.update(entity, key, val)
            else:
                break
    except Exception as e:
        print('oh no!',e)
    finally:
        global gevents
        if ws in gevents:
            gevent.kill(gevents[ws])

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    global gevents
    g = gevent.spawn(read_ws, ws)
    gevents[ws] = g
    myWorld.add_set_listener(SocketListenerThing(ws))


# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    return None

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    return None

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return None


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    return None



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
