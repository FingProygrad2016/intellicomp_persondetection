import json
import pika
from blinker import signal


# Mas info sobre RabbitMQ (implementacionde AMQP) en:
# http://www.rabbitmq.com/amqp-0-9-1-reference.html

dispatcher = signal('Dispatcher')


@dispatcher.connect
def real_send(args):
    args[0].send_message(args[1], args[2])


class Communicator:

    def __init__(self, queue_name=None, expiration_time=60,
                 host_address='localhost', exchange=None,
                 exchange_type='direct', routing_key=None):
        self.queue_name = queue_name
        self.expiration_time = str(expiration_time)
        self.connection = \
            pika.BlockingConnection(pika.ConnectionParameters(
                host=host_address))
        self.channel = self.connection.channel()

        if exchange:
            self.channel.exchange_declare(exchange, exchange_type=exchange_type)
            self.exchange = exchange

        if queue_name:
            self.channel.queue_declare(queue=queue_name)
            if routing_key:
                self.channel.queue_bind(queue=self.queue_name,
                                        exchange=self.exchange,
                                        routing_key=routing_key)
            self.exchange = ''
            # self.channel.queue_declare(queue=queue_name)

    def send_message(self, message, routing_key=None):
        self.channel.basic_publish(exchange=self.exchange,
                                   routing_key=routing_key or self.queue_name,
                                   body=message,
                                   properties=pika.BasicProperties(
                                   expiration=self.expiration_time))

    def apply(self, message, routing_key=None):
        if message:
            dispatcher.send([self, message.encode(), routing_key])

    def __delete__(self, instance):
        self.connection.close()

    def consume(self):
        return self.channel.consume(queue=self.queue_name, no_ack=True)
