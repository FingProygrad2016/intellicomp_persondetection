from hashlib import sha1
from datetime import datetime as dt

from multiprocessing import Process
import pika

from patternmaster.__main__ import PatternMaster
from trackermaster.__main__ import track_source
from utils.communicator import Communicator
from webmanager import socketio, app

# REFERENCIAS
# https://docs.python.org/3.5/library/multiprocessing.html#multiprocessing.pool.Pool
# http://sebastianraschka.com/Articles/2014_multiprocessing_intro.html#The-Pool-class


def log(msg):
    print('::MASTER:: %s' % msg)

def websocket_exposer():
    socketio.run(app, port=5000)


def pattern_recognition_launcher():
    pm = PatternMaster()
    pm.apply()


def create_queue(q_name):
    connection = pika.BlockingConnection()
    channel = connection.channel()
    return channel.basic_get(q_name)

if __name__ == '__main__':

    streamings = {}

    # Starting up the base

    warnings_queue = Communicator(queue_name='master_rcv', exchange='to_master',
                                  routing_key='#', exchange_type='topic')

    log("Starting up the Pattern Recognition Engine...")
    pattern_master = Process(target=pattern_recognition_launcher)
    pattern_master.start()

    log("Starting up the web manager...")
    web_exposer = Process(target=websocket_exposer)
    web_exposer.start()

    log("Espero el resultado")

    for method, properties, msg in warnings_queue.consume():
        if method.routing_key == 'cmd':
            cmd = msg.decode().split(' ')
            if cmd[0] == 'EXIT':
                pattern_master.terminate()
                web_exposer.terminate()
                [x.terminate() for x in streamings]
                break
            elif cmd[0] == 'SOURCE' and cmd[1] == 'NEW':
                if len(cmd) > 3:
                    # Se le pasa un id
                    identifier = cmd[3]
                else:
                    identifier = \
                        sha1(str(dt.utcnow()).encode('utf-8')).hexdigest()

                streamings[identifier] = Process(
                    target=track_source, args=[identifier, cmd[2]])
                streamings[identifier].start()

            elif cmd[0] == 'SOURCE' and cmd[1] == 'TERMINATE':
                if len(cmd) > 2:
                    streamings[cmd[2]].terminate()
                    del streamings[cmd[2]]
        else:
            log('WARNING %s' % msg)

    del warnings_queue

    log("Fin de Master Luncher.")
