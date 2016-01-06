from random import randint
from flask import Flask
from flask.ext.socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)


@app.route('/')
def main():
    return "Esta up", 200


@socketio.on('connect', namespace='/dd')
def ws_conn():
    socketio.emit('msg', {'randomnum': randint(100)}, namespace='/dd')


@socketio.on('disconnect', namespace='/dd')
def ws_disconn():
    socketio.emit('msg', {'randomnum': randint(100)}, namespace='/dd')


@socketio.on('new_random', namespace='/dd')
def ws_city(message):
    socketio.emit('msg', {'randomnum': randint(100)}, namespace="/dd")
