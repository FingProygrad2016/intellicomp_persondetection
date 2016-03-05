import configparser
import os
import inspect


def read_conf():
    configuration = configparser.ConfigParser()
    conf_file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    conf_file_path += '/patternmaster.conf'
    configuration.read(conf_file_path)

    return configuration['DEFAULT']


class CustomConfig:

    def __init__(self, custome_conf):
        self.custome_config = custome_conf

    def get(self, name):
        return self.custome_config[name.lower()]

    def getint(self, name):
        return int(self.custome_config[name.lower()])

    def getfloat(self, name):
        return float(self.custome_config[name.lower()])

    def getboolean(self, name):
        return bool(self.custome_config[name.lower()])
