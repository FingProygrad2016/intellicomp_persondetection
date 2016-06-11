
# To see opened connections, use command: lsof -a -i -c python3.5
import json

from flask import Flask, render_template, request
from flask.ext.socketio import SocketIO

from utils.communicator import Communicator
from trackermaster.config import read_conf as configs_tracker
from patternmaster.config import read_conf as configs_pattern


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '#$%*(0987654@#$%_top_secret_key_*&$#@'
    app.config['DEBUG'] = False
    global socketio
    socketio = SocketIO(app)

    return app, socketio


app, socketio = create_app()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/events', methods=['POST'])
def receive_events():
    data = json.loads(request.data.decode())
    method = data['method']
    msg = data['msg']
    global socketio
    if method == 'cmd':
        socketio.emit('cmd', {'data': msg}, broadcast=True)
    elif method == 'warnings':
        socketio.emit('warning', {'data': msg}, broadcast=True)
    elif method == 'info':
        socketio.emit('info', {'data': msg}, broadcast=True)
    elif method == 'img':
        socketio.emit('img', {'data': msg}, broadcast=True)

    return "OK", 200


@app.route('/configs')
def get_configs():
    return json.dumps(
        dict(trackermaster=[list(x) for x in dict(configs_tracker()).items()],
             patternmaster=[list(x) for x in
                            dict(configs_pattern()).items()])), 200


@socketio.on('connect')
def connect():
    print('connected')


@socketio.on('disconnect')
def disconnect():
    print('disconnected')


@socketio.on('cmd')
def ws_disconn(data):
    comm = Communicator(exchange='to_master', routing_key='cmd',
                        exchange_type='topic')
    comm.send_message(data['data'], routing_key='cmd')


def run_app():
    socketio.run(app, host='0.0.0.0')

if __name__ == '__main__':
    run_app()
