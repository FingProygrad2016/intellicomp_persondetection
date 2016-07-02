#!/bin/python3

import re
from sys import argv

def parse_mot_results(file_path='MOT_results.txt'):

    tests = {}

    with open(file_path, 'r') as f:
        l = f.readline()
        while not l.startswith('Evaluating ... '):
            l = f.readline()

        pos = 1
        for l in f:
            # print "pos: %s line: %s" % (pos, l)
            if pos == 1 and (l.startswith('*****') or l == "\n"):
                # Fin del archivo
                break
            elif pos == 1:
                id = re.search(".*\.\.\. (.*)-positions", l).group(1)
            elif pos == 5:
                values = re.search("\s*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*([0-9\.]*)[\|\s]*", l).groups()
            elif pos == 6:
                # Termina el bloque
                tests[id] = values
                pos = 0

            pos += 1

        return tests

if __name__ == "__main__":
    if len(argv) == 2:
        mot_result_path = argv[1]
    else:
        print("must be: python mot_results_parser.py file_path/file_name")
        exit()

    tests = parse_mot_results(mot_result_path)

    with open(mot_result_path + "2", 'w') as f:
        f.write(str(tests))
