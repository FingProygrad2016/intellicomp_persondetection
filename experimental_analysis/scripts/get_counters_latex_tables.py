#!/usr/bin/python3

import os
import re
from sys import argv

import math
import colorsys
from decimal import *

if len(argv) == 2:
    directory_of_results = argv[1]
else:
	print("must be: python get_counters_latex_tables.py directory_of_results")
	exit()

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



latex_table_template = """
	{\\renewcommand{\\arraystretch}{1.2}
	\\begin{table}
	\\begin{adjustwidth}{-1.5cm}{}
	\\begin{tabular}{c c | c@{ }*{2}{@{ }c@{ }} | c@{ }*{2}{@{ }c@{ }} | c@{ }*{2}{@{ }c@{ }}}
	\\multirow{2}{*}{Bloque} & \\multirow{2}{*}{Conf} & 
	\\multicolumn{3}{c|}{Nro. de Personas vs GT} & 
	\\multicolumn{3}{c|}{Nro. de Tracklets vs GT} & 
	\\multicolumn{3}{c}{Nro. interpolado vs GT} \\\\
	\\cline{3-11}
	& & Media & M\\'inima & M\\'axima & Media & M\\'inima & M\\'axima & Media & M\\'inima & M\\'axima \\\\
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

	\\begin{document}
"""

blocks_info = []

module_block_config_matcher = re.compile('(.+?)-.*-B(\d+?)-(\d+)')

float_matcher = '[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?'

info_matcher_one = '.*:\s('+float_matcher+'),\s('+float_matcher+'),\s('+float_matcher+')'
info_matcher_all = re.compile(info_matcher_one + info_matcher_one + info_matcher_one)

module_name = None
for file in os.listdir(directory_of_results + "differences/data"):
	if file.endswith("_diff.txt"):
		mbc = module_block_config_matcher.match(file)
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

		f = open(directory_of_results + "differences/data/" + file, "r")
		
		file_info = f.read()
		file_info = file_info.replace('\n', ' ').replace('\r', ' ')

		times = info_matcher_all.match(file_info)

		metric1 = {
			'mean': float(times.group(1)),
			'min': float(times.group(2)),
			'max': float(times.group(3))
		}
		metric2 = {
			'mean': float(times.group(4)),
			'min': float(times.group(5)),
			'max': float(times.group(6))
		}
		metric3 = {
			'mean': float(times.group(7)),
			'min': float(times.group(8)),
			'max': float(times.group(9))
		}

		block_info[config_in_block - 1] = " & " + str(config_in_block) + \
			" & " + "%.2f" % round(metric1['mean'],2) + " & " + "%.2f" % round(metric1['min'],2) + " & " + "%.2f" % round(metric1['max'],2) + \
			" & " + "%.2f" % round(metric2['mean'],2) + " & " + "%.2f" % round(metric2['min'],2) + " & " + "%.2f" % round(metric2['max'],2) + \
			" & " + "%.2f" % round(metric3['mean'],2) + " & " + "%.2f" % round(metric3['min'],2) + " & " + "%.2f" % round(metric3['max'],2) + "\\\\\n"

latex_rows = ""

for (i, block_info) in enumerate(blocks_info):
	block_diffs = ""
	for (j, config_info) in enumerate(block_info):
		block_diffs += config_info

	latex_rows += latex_table_multirow_template.replace('$1', '3').replace('$2', str(i + 1)).replace('$3', block_diffs)

latex_document += latex_table_template.replace('$1', latex_rows).replace('$2', module_name + ", diferencias contra el Ground Truth (GT) en el conteo de personas, seg\\'un las tres m\\'etricas.")
latex_document += "\\end{document}\n"

with open(directory_of_results + "differences/latex_counter_diff_tables.tex", 'w') as out:
	out.write(latex_document)
