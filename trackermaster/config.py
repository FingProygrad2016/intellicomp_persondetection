import configparser


def read_conf():
    configuration = configparser.ConfigParser()
    conf_file_path = 'trackermaster/trackermaster.conf'
    read_conf_files = configuration.read(conf_file_path)

    if not read_conf_files:
        raise Exception('Config. file %s not found.', conf_file_path)

    return configuration['DEFAULT']

config = read_conf()