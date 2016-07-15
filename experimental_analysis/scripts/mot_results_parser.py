#!/bin/python3

import re
import os
from sys import argv

import math
import colorsys
from decimal import *

def transition(value, minimum, maximum, start_point, end_point):
    if minimum < 0:
        maximum += -minimum
        value += -minimum
        minimum = 0
    if maximum == 0:
        return start_point
    return float(Decimal(start_point) + Decimal(end_point - start_point)*Decimal(value - minimum)/Decimal(maximum - minimum))

"""
def transition3(value, minimum, maximum, start_color_hsv, end_color_hsv):
    r1 = transition(value, minimum, maximum, start_color_hsv[0], end_color_hsv[0])
    r2 = transition(value, minimum, maximum, start_color_hsv[1], end_color_hsv[1])
    r3 = transition(value, minimum, maximum, start_color_hsv[2], end_color_hsv[2])
    return r1, r2, r3

colors_extreme = [(0, 255, 0), (255, 0, 0)]

start_triplet = colorsys.rgb_to_hsv(62, 220, 29) # 78, 209, 51) # comment: green converted to HSV
end_triplet = colorsys.rgb_to_hsv(213, 31, 49) # 187, 58, 69) # comment: accordingly for red
"""

def convert_to_rgb(min_max_values, config_number, module, val, precision, invert): # minval, maxval, val): # block_info['average_times'], 'BS', average_times['BS']
    """
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
    """

    minval = min_max_values['min_values'][module]['value']
    maxval = min_max_values['max_values'][module]['value']

    opacity = int(transition(val, minval, maxval, 0, 100))

    if invert:
        opacity = 100 - opacity

    number_formatter = "%."+str(precision)+"f"

    if opacity >= 45:
        return "\\color{white}{\\cellcolor{black!" + str(opacity) + "}{" + number_formatter % round(val, precision) + "}}"
    else:
        return "\\cellcolor{black!" + str(opacity) + "}{" + number_formatter % round(val, precision) + "}"

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
        % {
        % \\renewcommand{\\arraystretch}{1.0}
        % \\begin{adjustwidth}{-1.5cm}{}
        % \\begin{longtable}{@{}c@{ }@{}c@{ } | c@{ }*{2}{@{}c@{ }} | c@{ }*{3}{@{}c@{ }} | c@{ }*{3}{@{}c@{ }} | c@{ }*{2}{@{}c@{ }}}
        \\begin{landscape}
        \\noindent\\begin{longtabu} to \\linewidth{c c | *{3}{c} | *{4}{c} | *{4}{c} | *{3}{c}}
        Bloque & Conf & 
        Rcll & Prcn & FAR & 
        GT & MT & PT & ML & 
        FP & FN & IDs & FM & 
        MOTA & MOTP & MOTAL\\\\
        \\tabucline-
        $1
        \\caption{$2}
        % \\end{longtable}
        % \\end{adjustwidth}
        \\end{longtabu}
        \\end{landscape}
        % }
    """

    latex_table_multirow_template = """
        $3 \\tabucline-
    """

    latex_document = """
        \\documentclass{article}
        \\usepackage[utf8]{inputenc}

        \\usepackage{multirow}
        \\usepackage{changepage}
        % \\usepackage{longtable}
        \\usepackage{tabu}
        \\usepackage{lscape}
        \\usepackage{xcolor,colortbl}

        \\begin{document}
    """

    blocks_info = []

    module_block_config_matcher = re.compile('(.+?)-.*-B(\d+?)-(\d+)')

    infinite = 9999

    module_name = None
    for config in tests:
        mbc = module_block_config_matcher.match(config)
        module_name = mbc.group(1).replace('_', ' ')
        block_number = int(mbc.group(2))
        config_in_block = int(mbc.group(3))

        block_info_template = {
            'min_values': {
                'v0': {'value': infinite, 'config': -1},
                'v1': {'value': infinite, 'config': -1},
                'v2': {'value': infinite, 'config': -1},
                'v3': {'value': infinite, 'config': -1},
                'v4': {'value': infinite, 'config': -1},
                'v5': {'value': infinite, 'config': -1},
                'v6': {'value': infinite, 'config': -1},
                'v7': {'value': infinite, 'config': -1},
                'v8': {'value': infinite, 'config': -1},
                'v9': {'value': infinite, 'config': -1},
                'v10': {'value': infinite, 'config': -1},
                'v11': {'value': infinite, 'config': -1},
                'v12': {'value': infinite, 'config': -1},
                'v13': {'value': infinite, 'config': -1}
            },
            'max_values': {
                'v0': {'value': 0, 'config': -1},
                'v1': {'value': 0, 'config': -1},
                'v2': {'value': 0, 'config': -1},
                'v3': {'value': 0, 'config': -1},
                'v4': {'value': 0, 'config': -1},
                'v5': {'value': 0, 'config': -1},
                'v6': {'value': 0, 'config': -1},
                'v7': {'value': 0, 'config': -1},
                'v8': {'value': 0, 'config': -1},
                'v9': {'value': 0, 'config': -1},
                'v10': {'value': 0, 'config': -1},
                'v11': {'value': 0, 'config': -1},
                'v12': {'value': 0, 'config': -1},
                'v13': {'value': 0, 'config': -1}
            },
            'configs': []
        }
        config_template = {
            'v0': 0,
            'v1': 0,
            'v2': 0,
            'v3': 0,
            'v4': 0,
            'v5': 0,
            'v6': 0,
            'v7': 0,
            'v8': 0,
            'v9': 0,
            'v10': 0,
            'v11': 0,
            'v12': 0,
            'v13': 0
        }

        if len(blocks_info) < block_number:
            for i in range(0, block_number - len(blocks_info)):
                blocks_info.append(block_info_template)

        block_info = blocks_info[block_number - 1]

        if len(block_info['configs']) < config_in_block:
            for i in range(0, config_in_block - len(block_info['configs'])):
                block_info['configs'].append(config_template.copy())

        config_info = block_info['configs'][config_in_block - 1]

        values = tests[config]

        for i in range(0,14):
            f = float(values[i])
            column = 'v' + str(i)
            config_info[column] = f
            if float(values[i]) < block_info['min_values'][column]['value']:
                block_info['min_values'][column]['value'] = float(values[i])
                block_info['min_values'][column]['config'] = config_in_block
            if float(values[i]) > block_info['max_values'][column]['value']:
                block_info['max_values'][column]['value'] = float(values[i])
                block_info['max_values'][column]['config'] = config_in_block

    latex_rows = ""

    for (i, block_info) in enumerate(blocks_info):
        block_values = ""

        block_values += " & " + "mejor" + \
            " & " + "%.1f" % block_info['max_values']['v0']['value'] + \
            " & " + "%.1f" % block_info['max_values']['v1']['value'] + \
            " & " + "%.2f" % block_info['min_values']['v2']['value'] + \
            " & " + "N/A" + \
            " & " + "%.0f" % block_info['max_values']['v4']['value'] + \
            " & " + "%.0f" % block_info['max_values']['v5']['value'] + \
            " & " + "%.0f" % block_info['min_values']['v6']['value'] + \
            " & " + "%.0f" % block_info['min_values']['v7']['value'] + \
            " & " + "%.0f" % block_info['min_values']['v8']['value'] + \
            " & " + "%.0f" % block_info['min_values']['v9']['value'] + \
            " & " + "%.0f" % block_info['min_values']['v10']['value'] + \
            " & " + "%.1f" % block_info['max_values']['v11']['value'] + \
            " & " + "%.1f" % block_info['max_values']['v12']['value'] + \
            " & " + "%.1f" % block_info['max_values']['v13']['value'] + "\\\\\n"

        block_values += " & " + "peor" + \
            " & " + "%.1f" % block_info['min_values']['v0']['value'] + \
            " & " + "%.1f" % block_info['min_values']['v1']['value'] + \
            " & " + "%.2f" % block_info['max_values']['v2']['value'] + \
            " & " + "N/A" + \
            " & " + "%.0f" % block_info['min_values']['v4']['value'] + \
            " & " + "%.0f" % block_info['min_values']['v5']['value'] + \
            " & " + "%.0f" % block_info['max_values']['v6']['value'] + \
            " & " + "%.0f" % block_info['max_values']['v7']['value'] + \
            " & " + "%.0f" % block_info['max_values']['v8']['value'] + \
            " & " + "%.0f" % block_info['max_values']['v9']['value'] + \
            " & " + "%.0f" % block_info['max_values']['v10']['value'] + \
            " & " + "%.1f" % block_info['min_values']['v11']['value'] + \
            " & " + "%.1f" % block_info['min_values']['v12']['value'] + \
            " & " + "%.1f" % block_info['min_values']['v13']['value'] + "\\\\\n"

        block_values += "\\tabucline{2-16}"
        block_values += "\\tabucline{2-16}"

        configs_left = len(block_info['configs'])
        multirow_size = 27

        for (j, config_info) in enumerate(block_info['configs']):
            if multirow_size % 27 == 0:
                if configs_left < 27:
                    multirow_size = configs_left
                else:
                    multirow_size = 27

                block_number_text = "\\multirow{" + str(multirow_size) + "}{*}{" + str(i + 1) + "} "
                block_values += block_number_text

            block_values += " & " + str(j + 1) + \
                " & " + convert_to_rgb(block_info, j + 1, 'v0', config_info['v0'], 1, True) + \
                " & " + convert_to_rgb(block_info, j + 1, 'v1', config_info['v1'], 1, True) + \
                " & " + convert_to_rgb(block_info, j + 1, 'v2', config_info['v2'], 2, False) + \
                " & " + "%.0f" % config_info['v3'] + \
                " & " + convert_to_rgb(block_info, j + 1, 'v4', config_info['v4'], 0, True) + \
                " & " + "%.0f" % config_info['v5'] + \
                " & " + convert_to_rgb(block_info, j + 1, 'v6', config_info['v6'], 0, False) + \
                " & " + convert_to_rgb(block_info, j + 1, 'v7', config_info['v7'], 0, False) + \
                " & " + convert_to_rgb(block_info, j + 1, 'v8', config_info['v8'], 0, False) + \
                " & " + convert_to_rgb(block_info, j + 1, 'v9', config_info['v9'], 0, False) + \
                " & " + convert_to_rgb(block_info, j + 1, 'v10', config_info['v10'], 0, False) + \
                " & " + convert_to_rgb(block_info, j + 1, 'v11', config_info['v11'], 1, True) + \
                " & " + convert_to_rgb(block_info, j + 1, 'v12', config_info['v12'], 1, True) + \
                " & " + convert_to_rgb(block_info, j + 1, 'v13', config_info['v13'], 1, True) + "\\\\\n"
            block_values += "\\tabucline{2-16}"

            configs_left -= 1
            multirow_size -= 1

        latex_rows += latex_table_multirow_template.replace('$3', block_values)

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
