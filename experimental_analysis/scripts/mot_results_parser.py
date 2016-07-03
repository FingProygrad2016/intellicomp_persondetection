#!/bin/python3

import re
from sys import argv

def parse_mot_results(file_path):

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
                values = re.search("\s*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*([\-0-9\.]*)[\|\s]*", l).groups()
            elif pos == 6:
                # Termina el bloque
                tests[id] = values
                pos = 0

            pos += 1

        return tests

def parsed_results_to_latex_table(tests):
    latex_table_template = """
        {\\renewcommand{\\arraystretch}{1.2}
        \\begin{table}
        \\begin{adjustwidth}{-1.5cm}{}
        \\begin{tabular}{@{ }c@{ }@{ }c@{ } | c@{ }*{2}{@{ }c@{ }} | c@{ }*{3}{@{ }c@{ }} | c@{ }*{3}{@{ }c@{ }} | c@{ }*{2}{@{ }c@{ }}}
        Bloque & Conf & 
        Rcll & Prcn & FAR & 
        GT & MT & PT & ML & 
        FP & FN & IDs & FM & 
        MOTA & MOTP & MOTAL\\\\
        \\hline
        $1
        \\end{tabular}
        \\caption{$2}
        \\end{adjustwidth}
        \\end{table}
        }
    """

    latex_table_multirow_template = """
        \\multirow{$1}{*}{$2}
        $3 \\hline
    """

    latex_document = """
        \\documentclass{article}
        \\usepackage[utf8]{inputenc}

        \\usepackage{multirow}
        \\usepackage{changepage}

        \\begin{document}
    """
    blocks_info = []

    module_block_config_matcher = re.compile('(.+?)-.*-B(\d+?)-(\d+)')

    module_name = None
    for config in tests:
        mbc = module_block_config_matcher.match(config)
        module_name = mbc.group(1).replace('_', ' ')
        block_number = int(mbc.group(2))
        config_in_block = int(mbc.group(3))

        if len(blocks_info) < block_number:
            for i in range(0, block_number - len(blocks_info)):
                blocks_info.append([])

        block_info = blocks_info[block_number - 1]

        if len(block_info) < config_in_block:
            for i in range(0, config_in_block - len(block_info)):
                block_info.append("")

        values = tests[config]
        
        block_info[config_in_block - 1] = " & " + str(config_in_block) + \
            " & " + values[0] + " & " + values[1] + " & " + values[2] + \
            " & " + values[3] + " & " + values[4] + " & " + values[5] + " & " + values[6] + \
            " & " + values[7] + " & " + values[8] + " & " + values[9] + " & " + values[10] + \
            " & " + values[11] + " & " + values[12] + " & " + values[13] + "\\\\\n"

    latex_rows = ""

    for (i, block_info) in enumerate(blocks_info):
        block_values = ""
        for (j, config_info) in enumerate(block_info):
            block_values += config_info
        latex_rows += latex_table_multirow_template.replace('$1', str(len(block_info))).replace('$2', str(i + 1)).replace('$3', block_values)

    latex_document += latex_table_template.replace('$1', latex_rows).replace('$2', module_name + ", resultados del MOT Challenge.")
    latex_document += "\\end{document}\n"

    return latex_document

if __name__ == "__main__":
    if len(argv) == 2:
        directory_of_results = argv[1]
    else:
        print("must be: python mot_results_parser.py directory_of_results")
        exit()

    tests = parse_mot_results(directory_of_results + "data/MOT_results.txt")

    latex_document = parsed_results_to_latex_table(tests)

    with open(directory_of_results + "latex_MOT_results_table.tex", 'w') as f:
        f.write(latex_document)
