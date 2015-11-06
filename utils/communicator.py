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

    def __init__(self, queue_name='track_info', expiration_time=60):
        self.queue_name = queue_name
        self.expiration_time = str(expiration_time)
        self.connection = \
            pika.BlockingConnection(pika.ConnectionParameters(
                host=HOST_ADDRESS))
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue=queue_name)

    def send_message(self, message):
        self.channel.basic_publish(exchange='', routing_key=self.queue_name,
                                   body=message,
                                   properties=pika.BasicProperties(
                                       expiration=self.expiration_time))

    def apply(self, message):
        if message:
            dispatcher.send([self, message.encode()])

    def __delete__(self, instance):
        self.connection.close()