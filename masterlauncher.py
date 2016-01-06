import inspect
import os
from hashlib import sha1
from datetime import datetime as dt

from multiprocessing import Pool
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

    video_muestra = os.path.dirname(os.path.abspath(
        inspect.getfile(inspect.currentframe()))) + '/Videos/Video_003.avi'
    sources = [video_muestra,
               'http://live.cdn.antel.net.uy/auth_0_s2ujmpsk,vxttoken=cGF0aFVSS'
               'T0lMkZhdXRoXzBfczJ1am1wc2slMkZobHMlMkYlMkEmZXhwaXJ5PTE0NTAzMzkz'
               'OTUmcmFuZG9tPVFBYm0xTkhFMmUmYy1pcD0xOTAuNjQuNDkuMjcsMTA5ZjhjZjE'
               'wZjBhM2JkYTYzZjg5ZDRiNGI0YTY3MTNlZmZkMzUxNmRlZTQ5MTM3MmYxMWQ1Nz'
               'MyYWNmY2UzYw==/hls/var3300000/playlist.m3u8',
               'http://live.cdn.antel.net.uy/auth_0_dx1slhds,vxttoken=cGF0aFVSS'
               'T0lMkZhdXRoXzBfZHgxc2xoZHMlMkZobHMlMkYlMkEmZXhwaXJ5PTE0NTAzMzk2'
               'MzQmcmFuZG9tPU9Gb1N5MmhTWUsmYy1pcD0xOTAuNjQuNDkuMjcsZGU3Yjg3ZWI'
               '0OGY3ZWE5MmZhNDdjMTk0YWIzOGM3ODBkYjQ1ZDc4OTExYjdjY2I1NGE3MGJhM2'
               'YzZjhmZWRlZg==/hls/var3300000/playlist.m3u8']

    # Starting up the base

    warnings_queue = Communicator(queue_name='to_master')

    log("Starting up Pool of processes...")
    processes_pool = Pool()

    log("Starting up the Pattern Recognition Engine...")
    pattern_master = processes_pool.apply_async(pattern_recognition_launcher)

    log("Starting up the web manager...")
    webs_exposer = processes_pool.apply_async(websocket_exposer)

    # log("Opening every stream to process...")
    # cam1 = processes_pool.map_async(track_source, sources)

    log("Espero el resultado")

    for method, properties, msg in warnings_queue.consume():
        if method.routing_key == 'cmd':
            cmd = msg.split(' ')
            if cmd[0] == 'EXIT':
                break
            elif cmd[0] == 'SOURCE' and cmd[1] == 'NEW':
                if len(cmd) > 3:
                    # Se le pasa un id
                    identifier = cmd[3]
                else:
                    identifier = \
                        sha1(str(dt.utcnow()).encode('utf-8')).hexdigest()

                streamings[identifier] = processes_pool.apply_async(
                    track_source, args=[identifier, cmd[2]])
            elif cmd[0] == 'SOURCE' and cmd[1] == 'TERMINATE':
                if len(cmd) > 2:
                    streamings[cmd[2]].terminate()
        else:
            log('WARNING %s' % msg)

    del warnings_queue

    pattern_master.terminate()
    webs_exposer.terminate()
    map(lambda x: x.terminate(), streamings.values())

    log("Fin de Master Luncher.")
