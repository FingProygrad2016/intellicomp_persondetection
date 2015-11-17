import configparser


def read_conf():
    configuration = configparser.ConfigParser()
    configuration.read('./patternmaster.conf')

    return configuration['DEFAULT']

config = read_conf()