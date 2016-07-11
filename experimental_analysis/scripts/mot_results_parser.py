#!/bin/python3

import re
import os
from sys import argv

import math
import colorsys
from decimal import *

def transition(value, minimum, maximum, start_point, end_point):
    return float(Decimal(start_point) + Decimal(end_point - start_point)*Decimal(value - minimum)/Decimal(maximum))

def transition3(value, minimum, maximum, start_color_hsv, end_color_hsv):
    r1 = transition(value, minimum, maximum, start_color_hsv[0], end_color_hsv[0])
    r2 = transition(value, minimum, maximum, start_color_hsv[1], end_color_hsv[1])
    r3 = transition(value, minimum, maximum, start_color_hsv[2], end_color_hsv[2])
    return r1, r2, r3

colors_extreme = [(0, 255, 0), (255, 0, 0)]

start_triplet = colorsys.rgb_to_hsv(62, 220, 29) # 78, 209, 51) # comment: green converted to HSV
end_triplet = colorsys.rgb_to_hsv(213, 31, 49) # 187, 58, 69) # comment: accordingly for red

def convert_to_rgb(min_max_values, config_number, module, val): # minval, maxval, val): # block_info['average_times'], 'BS', average_times['BS']

    minconfig = min_max_values['min_values'][module]['config']
    maxconfig = min_max_values['max_values'][module]['config']

    if minconfig == config_number:
        return "\cellcolor{rgb:red," + str(colors_extreme[0][0]) + ";green," + str(colors_extreme[0][1]) + ";blue," + str(colors_extreme[0][2]) + "}" + "%.5f" % round(val, 5)
    elif maxconfig == config_number:
        return "\cellcolor{rgb:red," + str(colors_extreme[1][0]) + ";green," + str(colors_extreme[1][1]) + ";blue," + str(colors_extreme[1][2]) + "}" + "%.5f" % round(val, 5)
    else:
        minval = min_max_values['min_values'][module]['value']
        maxval = min_max_values['max_values'][module]['value']

        hsv_color = transition3(val, minval, maxval, start_triplet, end_triplet)
        rgb_color = colorsys.hsv_to_rgb(hsv_color[0],hsv_color[1],hsv_color[2])

        return "\cellcolor{rgb:red," + str(rgb_color[0]) + ";green," + str(rgb_color[1]) + ";blue," + str(rgb_color[2]) + "}" + "%.5f" % round(val, 5)




def parse_mot_results(file_path, tests):

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

def parsed_results_to_latex_table(tests):
    latex_table_template = """
    {
        \\renewcommand{\\arraystretch}{1.0}
            % \\begin{adjustwidth}{-1.5cm}{}
                \\begin{longtable}{@{}c@{ }@{}c@{ } | c@{ }*{2}{@{}c@{ }} | c@{ }*{3}{@{}c@{ }} | c@{ }*{3}{@{}c@{ }} | c@{ }*{2}{@{}c@{ }}}
                    Bloque & Conf & 
                    Rcll & Prcn & FAR & 
                    GT & MT & PT & ML & 
                    FP & FN & IDs & FM & 
                    MOTA & MOTP & MOTAL\\\\
                    \\hline
                    $1
                    \\caption{$2}
                \\end{longtable}
            % \\end{adjustwidth}
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
\\usepackage{longtable}

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
        latex_rows += latex_table_multirow_template.replace('$1', '3').replace('$2', str(i + 1)).replace('$3', block_values)

    latex_document += latex_table_template.replace('$1', latex_rows).replace('$2', module_name + ", resultados del MOT Challenge.")
    latex_document += "\\end{document}\n"

    return latex_document

if __name__ == "__main__":
    if len(argv) == 2:
        directory_of_results = argv[1]
    else:
        print("must be: python mot_results_parser.py directory_of_results")
        exit()

    tests = {}

    for file in os.listdir(directory_of_results + "data"):
        if file.startswith('MOT_results'):
            parse_mot_results(directory_of_results + "data/" + file, tests)

    latex_document = parsed_results_to_latex_table(tests)

    with open(directory_of_results + "latex_MOT_results_table.tex", 'w') as f:
        f.write(latex_document)
