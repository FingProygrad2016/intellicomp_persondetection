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

config = read_conf()