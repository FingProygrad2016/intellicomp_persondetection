import json
import pika
from blinker import signal

HOST_ADDRESS = 'localhost'

# Mas info sobre RabbitMQ (implementacionde AMQP) en:
# http://www.rabbitmq.com/amqp-0-9-1-reference.html

dispatcher = signal('Dispatcher')


@dispatcher.connect
def real_send(args):
    args[0].send_message(args[1])


class Communicator:

    def __init__(self):
        self.connection = \
            pika.BlockingConnection(pika.ConnectionParameters(
                host=HOST_ADDRESS))
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue='track_info')

    def send_message(self, message):
        self.channel.basic_publish(exchange='', routing_key='track_info',
                                   body=message,
                                   properties=pika.BasicProperties(
                                       expiration='60'))

    def apply(self, message):
        if message:
            dispatcher.send([self, json.dumps(message)])

    def __delete__(self, instance):
        self.connection.close()