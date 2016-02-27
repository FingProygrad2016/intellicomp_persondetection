import sys
import os
import json
import pika

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)

from patternmaster.pattern_recognition import PatternRecognition
from patternmaster.config import config


class PatternMaster(object):

    pattern_recognition = {}

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=config.get('TRACK_INFO_QUEUE_HOSTADDRESS')))
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue=config.get('TRACK_INFO_QUEUE_NAME'))

    def apply(self):
        self.channel.basic_consume(self.proccess, queue='track_info',
                                   no_ack=True)
        self.channel.start_consuming()

    @staticmethod
    def proccess(ch, method, properties, body):
        tracklets = json.loads(body.decode())
        for info in tracklets:
            identifier = info['tracker_id']
            if identifier not in PatternMaster.pattern_recognition:
                PatternMaster.pattern_recognition[identifier] = \
                    PatternRecognition(identifier,
                                       config.getint('MIN_ANGLE_ROTATION'),
                                       config.getint('MIN_WALKING_SPEED'),
                                       config.getint('MIN_RUNNING_SPEED'))

            PatternMaster.pattern_recognition[identifier].apply(info)

    def __del__(self):
        self.connection.close()


if __name__ == "__main__":
    print("Listening...")
    PatternMaster().apply()
    print("END.")
