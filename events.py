import json
import requests
from utils.communicator import Communicator


def events_listener():
    warnings_queue = Communicator(queue_name='web_rcv', exchange='to_master',
                                  routing_key='#', exchange_type='topic')
    base_url = "http://127.0.0.1:5000"

    for method, properties, msg in warnings_queue.consume():
        data = {
            'method': method.routing_key,
            'msg': msg.decode()
        }
        try:
            requests.post(base_url + "/events", json.dumps(data))
        except Exception as e:
            print("Error sending the event to webmanager: %s" % str(e)[:100])

if __name__ == "__main__":
    events_listener()