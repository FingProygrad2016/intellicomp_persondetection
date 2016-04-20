import subprocess
from hashlib import sha1
from datetime import datetime as dt
import json

from multiprocessing import Process
import pika

from events import events_listener
from patternmaster.__main__ import PatternMaster
from streamcontroller import StreamController as SC
from utils.communicator import Communicator
from webmanager import run_app as run_webmanager

# REFERENCIAS
# https://docs.python.org/3.5/library/multiprocessing.html#multiprocessing.pool.Pool
# http://sebastianraschka.com/Articles/2014_multiprocessing_intro.html#The-Pool-class


def log(msg):
    print(msg)


def websocket_exposer():
    run_webmanager()


def pattern_recognition_launcher():
    pm = PatternMaster()
    pm.apply()


def create_queue(q_name):
    connection = pika.BlockingConnection()
    channel = connection.channel()
    return channel.basic_get(q_name)


stream_controller = SC()

if __name__ == '__main__':

    # Starting up the base

    warnings_queue = Communicator(queue_name='launcher_rcv',
                                  exchange='to_master', routing_key='#',
                                  exchange_type='topic')

    log("Starting up the Pattern Recognition Engine...")
    pattern_master = Process(target=pattern_recognition_launcher)
    pattern_master.start()

    log("Starting up the web manager...")
    web_exposer = Process(target=websocket_exposer)
    web_exposer.start()

    log("Starting up events sender...")
    events_listener_process = Process(target=events_listener)
    events_listener_process.start()

    log("Espero el resultado")

    for method, properties, msg in warnings_queue.consume():
        print(":::: STREAM CONTROLLER %s" % stream_controller)
        log('(TYPE %s) %s' %
            (method.routing_key, msg[:100]))
        if method.routing_key == 'cmd':
            cmd = msg.decode().split(' ')
            if cmd[0] == 'EXIT':
                pattern_master.terminate()
                web_exposer.terminate()
                events_listener_process.terminate()
                stream_controller.remove_all()
                break
            elif cmd[0] == 'SOURCE' and cmd[1] == 'NEW':
                if len(cmd) > 3:
                    # Se le pasa un id
                    identifier = cmd[3]
                else:
                    identifier = \
                        sha1(str(dt.utcnow()).encode('utf-8')).hexdigest()

                trackermaster_conf = json.loads(cmd[4]) \
                    if len(cmd) > 4 else None
                patternmaster_conf = json.loads(cmd[5]) \
                    if len(cmd) > 5 else None

                stream_controller.add(identifier, subprocess.Popen(
                    ["python3", "trackermaster", identifier, cmd[2],
                     json.dumps(trackermaster_conf),
                     json.dumps(patternmaster_conf)]))

            elif cmd[0] == 'SOURCE' and cmd[1] == 'TERMINATE':
                if len(cmd) > 2:
                    source_id = cmd[2]
                    stream_controller.remove(source_id)
            elif cmd[0] == 'SOURCE' and cmd[1] == 'LIST':
                comm = Communicator(exchange='to_master', exchange_type='topic')
                comm.send_message(json.dumps(dict(
                    info_id="SOURCE LIST",
                    content=list(stream_controller.get_identidiers()))),
                    routing_key='info')

    del warnings_queue

    log("Fin de Master Luncher.")
