import sys
from utils.communicator import Communicator

__author__ = 'jp'

if __name__ == '__main__':
    communicator = Communicator(queue_name='cmd', exchange='to_master',
                                exchange_type='topic', expiration_time=600)

    communicator.send_message(" ".join(sys.argv[1:]))
