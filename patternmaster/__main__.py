import sys
import os
path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)

import json
import pika

from patternmaster.pattern_recognition import PatternRecognition


class Receiver(object):

    pattern_recognition = PatternRecognition()

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost'))
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue='track_info')

    def apply(self):
        self.channel.basic_consume(self.proccess, queue='track_info',
                                   no_ack=True)
        self.channel.start_consuming()

    @staticmethod
    def proccess(ch, method, properties, body):
        tracklets = json.loads(body.decode())
        for info in tracklets:
            Receiver.pattern_recognition.apply(info)

    def __del__(self):
        self.connection.close()


if __name__ == "__main__":
    print("Listening...")
    Receiver().apply()
    print("END.")
