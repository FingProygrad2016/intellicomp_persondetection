import configparser
import os
import inspect


def read_conf():
    configuration = configparser.ConfigParser()
    conf_file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    conf_file_path += '/trackermaster.conf'
    read_conf_files = configuration.read(conf_file_path)

    if not read_conf_files:
        raise Exception('Config. file %s not found.', conf_file_path)

    return configuration['DEFAULT']

global custome_config
custome_config = None


class CustomConfig(object):
    data = read_conf()

    @classmethod
    def get(cls, name):
        if custome_config:
            return custome_config[name.lower()]
        return cls.data[name]

    @classmethod
    def getint(cls, name):
        if custome_config:
            return int(custome_config[name.lower()])
        return cls.data[name]

    @classmethod
    def getfloat(cls, name):
        if custome_config:
            return float(custome_config[name.lower()])
        return cls.data[name]

    @classmethod
    def getboolean(cls, name):
        if custome_config:
            return bool(custome_config[name.lower()])
        return cls.data[name]


def set_custome_config(data):
    global custome_config
    custome_config = data

config = CustomConfig
