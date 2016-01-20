from threading import Thread
from flask import Flask, render_template
from flask.ext.socketio import SocketIO
from utils.communicator import Communicator

app = Flask(__name__)
app.config['SECRET_KEY'] = '#$%*(0987654@#$%_top_secret_key_*&$#@'
socketio = SocketIO(app)
thread = None
warnings_queue = Communicator(queue_name='master_rcv', exchange='to_master',
                                  routing_key='#', exchange_type='topic')


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    for method, properties, msg in warnings_queue.consume():
        count += 1
        # socketio.emit('msg', {'data': msg, 'count': count})
        socketio.emit('msg', {'data': msg.decode()})

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
    print(data)
