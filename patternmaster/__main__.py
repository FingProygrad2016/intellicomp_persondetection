import sys
import os
import json
import pika

path = os.path.dirname(sys.modules[__name__].__file__)
path = os.path.join(path, '..')
sys.path.insert(0, path)

from patternmaster.pattern_recognition import PatternRecognition
from patternmaster.config import read_conf


class PatternMaster(object):

    pattern_recognition = {}
    pattern_recognition_settings = {}

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=read_conf().get('TRACK_INFO_QUEUE_HOSTADDRESS')))
        self.channel = self.connection.channel()

        self.channel.exchange_declare(
            exchange=read_conf().get('TRACK_INFO_EXCHANGE_NAME'),
            exchange_type='direct')

        self.channel.queue_declare(queue='patternmaster_rcv')

        self.channel.queue_bind(
            queue='patternmaster_rcv',
            exchange=read_conf().get('TRACK_INFO_EXCHANGE_NAME'),
            routing_key='processing_settings')
        self.channel.queue_bind(
            queue='patternmaster_rcv',
            exchange=read_conf().get('TRACK_INFO_EXCHANGE_NAME'),
            routing_key='track_info')

    def apply(self):
        self.channel.basic_consume(self.proccess, queue='patternmaster_rcv',
                                   no_ack=True)
        self.channel.start_consuming()

    @staticmethod
    def proccess(ch, method, properties, body):

        data = json.loads(body.decode())
        # if isinstance(data, list):
        #     for d in data:
        #         print("Process data: %s" % [x for x in d.items()
        #                                     if x[0] != 'img'])
        if method.routing_key == 'track_info':
            PatternMaster._process_tracklets(data)
        elif method.routing_key == 'processing_settings':
            PatternMaster._process_configs(data)

    def __del__(self):
        self.connection.close()

    @classmethod
    def _process_tracklets(cls, data):
        for info in data:
            identifier = info['tracker_id']
            if identifier not in cls.pattern_recognition:
                if identifier not in cls.pattern_recognition_settings:
                    # While processing settings has not arrived, skip
                    # the tracklets
                    continue
                custome_config = cls.pattern_recognition_settings[identifier]
                cls.pattern_recognition[identifier] = \
                    PatternRecognition(identifier, custome_config)

            PatternMaster.pattern_recognition[identifier].apply(info)

    @classmethod
    def _process_configs(cls, data):
        identifier = data['identifier']
        new_config = data['config']
        resolution_mult = data['resolution_multiplier']

        cls.pattern_recognition_settings[identifier] = new_config

        # If the instance of Pattern Recognition was already created,
        # update its configs values.
        if identifier in cls.pattern_recognition:
            cls.pattern_recognition[identifier].set_config(new_config,
                                                           resolution_mult)

if __name__ == "__main__":
    print("Listening...")
    PatternMaster().apply()
    print("END.")
