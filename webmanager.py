from threading import Thread
from flask import Flask, render_template
from flask.ext.socketio import SocketIO
from utils.communicator import Communicator

app = Flask(__name__)
app.config['SECRET_KEY'] = '#$%*(0987654@#$%_top_secret_key_*&$#@'
socketio = SocketIO(app)
thread = None

warnings_queue = Communicator(queue_name='web_rcv', exchange='to_master',
                              routing_key='#', exchange_type='topic')


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
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


@socketio.on('connect')
def ws_conn():
    return True
    # socketio.emit('msg', {'data': 'WELCOME ' + str(randint(100, 200))})


@socketio.on('cmd')
def ws_disconn(data):
    comm = Communicator(exchange='to_master', routing_key='cmd',
                        exchange_type='topic')
    comm.send_message(data['data'], routing_key='cmd')
    print(data)
