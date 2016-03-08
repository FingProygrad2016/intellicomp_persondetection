import json
from threading import Thread

from flask import Flask, render_template
from flask.ext.socketio import SocketIO

from utils.communicator import Communicator
from trackermaster.config import read_conf as configs_tracker
from patternmaster.config import read_conf as configs_pattern

app = Flask(__name__)
app.config['SECRET_KEY'] = '#$%*(0987654@#$%_top_secret_key_*&$#@'
socketio = SocketIO(app)
thread = None

warnings_queue = Communicator(queue_name='web_rcv', exchange='to_master',
                              routing_key='#', exchange_type='topic')


def background_thread():
    for method, properties, msg in warnings_queue.consume():
        if method.routing_key == 'cmd':
            socketio.emit('cmd', {'data': msg.decode()})
        elif method.routing_key == 'warnings':
            socketio.emit('warning', {'data': msg.decode()})
        elif method.routing_key == 'info':
            socketio.emit('info', {'data': msg.decode()})
        elif method.routing_key == 'img':
            socketio.emit('img', {'data': msg.decode()})


@app.route('/')
def index():
    global thread
    if thread is None:
        thread = Thread(target=background_thread)
        thread.daemon = True
        thread.start()
    return render_template('index.html')


@app.route('/configs')
def get_configs():
    return json.dumps(
        dict(trackermaster=[list(x) for x in dict(configs_tracker()).items()],
             patternmaster=[list(x) for x in
                            dict(configs_pattern()).items()])), 200


@socketio.on('connect')
def ws_conn():
    return True


@socketio.on('cmd')
def ws_disconn(data):
    comm = Communicator(exchange='to_master', routing_key='cmd',
                        exchange_type='topic')
    comm.send_message(data['data'], routing_key='cmd')


if __name__ == '__main__':
    app.run(debug=True)
    # app.run(debug=False)