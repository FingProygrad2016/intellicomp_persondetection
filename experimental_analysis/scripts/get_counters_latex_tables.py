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
    return math.floor(r1), math.floor(r2), math.floor(r3)

colors_extreme = [(0, 255, 0), (255, 0, 0)]

start_triplet = colorsys.rgb_to_hsv(62, 220, 29) # 78, 209, 51) # comment: green converted to HSV
end_triplet = colorsys.rgb_to_hsv(213, 31, 49) # 187, 58, 69) # comment: accordingly for red
"""

def convert_to_rgb(min_max_values, config_number, module, val, precision): # minval, maxval, val): # block_info['average_times'], 'BS', average_times['BS']

	"""
    minconfig = min_max_values['min_values'][module]['config']
    maxconfig = min_max_values['max_values'][module]['config']

    if minconfig == config_number:
        return "\cellcolor{rgb:red," + str(colors_extreme[0][0]) + ";green," + str(colors_extreme[0][1]) + ";blue," + str(colors_extreme[0][2]) + "}" + "%.2f" % round(val, 2)
   	elif maxconfig == config_number:
        return "\cellcolor{rgb:red," + str(colors_extreme[1][0]) + ";green," + str(colors_extreme[1][1]) + ";blue," + str(colors_extreme[1][2]) + "}" + "%.2f" % round(val, 2)
	
    else:
   	"""
	minval = min_max_values['min_values'][module]['value']
	maxval = min_max_values['max_values'][module]['value']

	"""
	hsv_color = transition3(val, minval, maxval, start_triplet, end_triplet)
	rgb_color = colorsys.hsv_to_rgb(hsv_color[0],hsv_color[1],hsv_color[2])

	return "\cellcolor{rgb:red," + str(rgb_color[0]) + ";green," + str(rgb_color[1]) + ";blue," + str(rgb_color[2]) + "}{" + "%.2f" % round(val, 2) + "}"
	"""

	opacity = int(transition(val, minval, maxval, 0, 100))

	number_formatter = "%."+str(precision)+"f"

	if opacity >= 45:
		return "\\color{white}{\\cellcolor{black!" + str(opacity) + "}{" + number_formatter % round(val, precision) + "}}"
	else:
		return "\\cellcolor{black!" + str(opacity) + "}{" + number_formatter % round(val, precision) + "}"



latex_table_template = """
	% {\\renewcommand{\\arraystretch}{1.2}
	% \\begin{adjustwidth}{-1.5cm}{}
	% \\begin{longtable}{c c | c@{ }*{2}{@{ }c@{ }} | c@{ }*{2}{@{ }c@{ }} | c@{ }*{2}{@{ }c@{ }}}
	\\begin{landscape}
	\\noindent\\begin{longtabu} to \\linewidth {c c | *{3}{c} | *{3}{c} | *{3}{c} }
	\\multirow{2}{*}{Bloque} & \\multirow{2}{*}{Conf} & 
	\\multicolumn{3}{c|}{Nro. de Personas vs GT} & 
	\\multicolumn{3}{c|}{Nro. de Tracklets vs GT} & 
	\\multicolumn{3}{c}{Nro. interpolado vs GT} \\\\
	\\tabucline{3-11}
	\\tabuphantomline
	& & Media & M\\'inima & M\\'axima & Media & M\\'inima & M\\'axima & Media & M\\'inima & M\\'axima \\\\
	\\tabucline-
	$1
	\\caption{$2}
	% \\end{adjustwidth}
	% \\end{longtable}
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
	% \\usepackage{longtable}
	\\usepackage{tabu}
	\\usepackage{lscape}
	\\usepackage{xcolor,colortbl}

	\\begin{document}
"""

blocks_info = []

module_block_config_matcher = re.compile('(.+?)-.*-B(\d+?)-(\d+)')

float_matcher = '[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?'

info_matcher_one = '.*:\s('+float_matcher+'),\s('+float_matcher+'),\s('+float_matcher+')'
info_matcher_all = re.compile(info_matcher_one + info_matcher_one + info_matcher_one)

infinite = 9999

module_name = None
for file in os.listdir(directory_of_results + "differences/data"):
	if file.endswith("_diff.txt"):
		mbc = module_block_config_matcher.match(file)
		module_name = mbc.group(1).replace('_', ' ')
		block_number = int(mbc.group(2))
		config_in_block = int(mbc.group(3))

		block_info_template = {
			'metric1': {'min_values': {
								'mean': {'value': infinite, 'config': -1},
								'min': {'value': infinite, 'config': -1},
								'max': {'value': infinite, 'config': -1}
								},
								'max_values': {
									'mean': {'value': 0, 'config': -1},
									'min': {'value': 0, 'config': -1},
									'max': {'value': 0, 'config': -1}
								}},
			'metric2': {'min_values': {
							'mean': {'value': infinite, 'config': -1},
							'min': {'value': infinite, 'config': -1},
							'max': {'value': infinite, 'config': -1}
							},
							'max_values': {
								'mean': {'value': 0, 'config': -1},
								'min': {'value': 0, 'config': -1},
								'max': {'value': 0, 'config': -1}
							}},
			'metric3': {'min_values': {
							'mean': {'value': infinite, 'config': -1},
							'min': {'value': infinite, 'config': -1},
							'max': {'value': infinite, 'config': -1}
							},
							'max_values': {
								'mean': {'value': 0, 'config': -1},
								'min': {'value': 0, 'config': -1},
								'max': {'value': 0, 'config': -1}
							}},
			'configs': []
		}
		config_template = {
			'metric1': {
				'mean': 0,
				'min': 0,
				'max': 0
			},
			'metric2': {
				'mean': 0,
				'min': 0,
				'max': 0
			},
			'metric3': {
				'mean': 0,
				'min': 0,
				'max': 0
			}
		}

		if len(blocks_info) < block_number:
			for i in range(0, block_number - len(blocks_info)):
				blocks_info.append(block_info_template)

		block_info = blocks_info[block_number - 1]

		if len(block_info['configs']) < config_in_block:
			for i in range(0, config_in_block - len(block_info['configs'])):
				block_info['configs'].append(config_template.copy())

		config_info = block_info['configs'][config_in_block - 1]

		f = open(directory_of_results + "differences/data/" + file, "r")
		
		file_info = f.read()
		file_info = file_info.replace('\n', ' ').replace('\r', ' ')

		times = info_matcher_all.match(file_info)

		metric1 = config_info['metric1']

		metric1['mean'] = float(times.group(1))
		if metric1['mean'] < block_info['metric1']['min_values']['mean']['value']:
			block_info['metric1']['min_values']['mean']['value'] = metric1['mean']
			block_info['metric1']['min_values']['mean']['config'] = config_in_block
		if metric1['mean'] > block_info['metric1']['max_values']['mean']['value']:
			block_info['metric1']['max_values']['mean']['value'] = metric1['mean']
			block_info['metric1']['max_values']['mean']['config'] = config_in_block

		metric1['min'] = float(times.group(2))
		if metric1['min'] < block_info['metric1']['min_values']['min']['value']:
			block_info['metric1']['min_values']['min']['value'] = metric1['min']
			block_info['metric1']['min_values']['min']['config'] = config_in_block
		if metric1['min'] > block_info['metric1']['max_values']['min']['value']:
			block_info['metric1']['max_values']['min']['value'] = metric1['min']
			block_info['metric1']['max_values']['min']['config'] = config_in_block

		metric1['max'] = float(times.group(3))
		if metric1['max'] < block_info['metric1']['min_values']['max']['value']:
			block_info['metric1']['min_values']['max']['value'] = metric1['max']
			block_info['metric1']['min_values']['max']['config'] = config_in_block
		if metric1['max'] > block_info['metric1']['max_values']['max']['value']:
			block_info['metric1']['max_values']['max']['value'] = metric1['max']
			block_info['metric1']['max_values']['max']['config'] = config_in_block

		metric2 = config_info['metric2']

		metric2['mean'] = float(times.group(4))
		if metric2['mean'] < block_info['metric2']['min_values']['mean']['value']:
			block_info['metric2']['min_values']['mean']['value'] = metric2['mean']
			block_info['metric2']['min_values']['mean']['config'] = config_in_block
		if metric2['mean'] > block_info['metric2']['max_values']['mean']['value']:
			block_info['metric2']['max_values']['mean']['value'] = metric2['mean']
			block_info['metric2']['max_values']['mean']['config'] = config_in_block

		metric2['min'] = float(times.group(5))
		if metric2['min'] < block_info['metric2']['min_values']['min']['value']:
			block_info['metric2']['min_values']['min']['value'] = metric2['min']
			block_info['metric2']['min_values']['min']['config'] = config_in_block
		if metric2['min'] > block_info['metric2']['max_values']['min']['value']:
			block_info['metric2']['max_values']['min']['value'] = metric2['min']
			block_info['metric2']['max_values']['min']['config'] = config_in_block

		metric2['max'] = float(times.group(6))
		if metric2['max'] < block_info['metric2']['min_values']['max']['value']:
			block_info['metric2']['min_values']['max']['value'] = metric2['max']
			block_info['metric2']['min_values']['max']['config'] = config_in_block
		if metric2['max'] > block_info['metric2']['max_values']['max']['value']:
			block_info['metric2']['max_values']['max']['value'] = metric2['max']
			block_info['metric2']['max_values']['max']['config'] = config_in_block

		metric3 = config_info['metric3']

		metric3['mean'] = float(times.group(7))
		if metric3['mean'] < block_info['metric3']['min_values']['mean']['value']:
			block_info['metric3']['min_values']['mean']['value'] = metric3['mean']
			block_info['metric3']['min_values']['mean']['config'] = config_in_block
		if metric3['mean'] > block_info['metric3']['max_values']['mean']['value']:
			block_info['metric3']['max_values']['mean']['value'] = metric3['mean']
			block_info['metric3']['max_values']['mean']['config'] = config_in_block

		metric3['min'] = float(times.group(8))
		if metric3['min'] < block_info['metric3']['min_values']['min']['value']:
			block_info['metric3']['min_values']['min']['value'] = metric3['min']
			block_info['metric3']['min_values']['min']['config'] = config_in_block
		if metric3['min'] > block_info['metric3']['max_values']['min']['value']:
			block_info['metric3']['max_values']['min']['value'] = metric3['min']
			block_info['metric3']['max_values']['min']['config'] = config_in_block

		metric3['max'] = float(times.group(9))
		if metric3['max'] < block_info['metric3']['min_values']['max']['value']:
			block_info['metric3']['min_values']['max']['value'] = metric3['max']
			block_info['metric3']['min_values']['max']['config'] = config_in_block
		if metric3['max'] > block_info['metric3']['max_values']['max']['value']:
			block_info['metric3']['max_values']['max']['value'] = metric3['max']
			block_info['metric3']['max_values']['max']['config'] = config_in_block
		
latex_rows = ""

for (i, block_info) in enumerate(blocks_info):
	block_diffs = ""

	block_diffs += " & " + "mejor" + \
		" & " + "%.2f" % block_info['metric1']['min_values']['mean']['value'] + \
		" & " + "%.0f" % block_info['metric1']['min_values']['min']['value'] + \
		" & " + "%.0f" % block_info['metric1']['min_values']['max']['value'] + \
		" & " + "%.2f" % block_info['metric2']['min_values']['mean']['value'] + \
		" & " + "%.0f" % block_info['metric2']['min_values']['min']['value'] + \
		" & " + "%.0f" % block_info['metric2']['min_values']['max']['value'] + \
		" & " + "%.2f" % block_info['metric3']['min_values']['mean']['value'] + \
		" & " + "%.0f" % block_info['metric3']['min_values']['min']['value'] + \
		" & " + "%.0f" % block_info['metric3']['min_values']['max']['value'] + "\\\\\n"

	block_diffs += " & " + "peor" + \
		" & " + "%.2f" % block_info['metric1']['max_values']['mean']['value'] + \
		" & " + "%.0f" % block_info['metric1']['max_values']['min']['value'] + \
		" & " + "%.0f" % block_info['metric1']['max_values']['max']['value'] + \
		" & " + "%.2f" % block_info['metric2']['max_values']['mean']['value'] + \
		" & " + "%.0f" % block_info['metric2']['max_values']['min']['value'] + \
		" & " + "%.0f" % block_info['metric2']['max_values']['max']['value'] + \
		" & " + "%.2f" % block_info['metric3']['max_values']['mean']['value'] + \
		" & " + "%.0f" % block_info['metric3']['max_values']['min']['value'] + \
		" & " + "%.0f" % block_info['metric3']['max_values']['max']['value'] + "\\\\\n"

	block_diffs += "\\tabucline{2-11}"
	block_diffs += "\\tabucline{2-11}"

	configs_left = len(block_info['configs'])
	multirow_size = 27

	for (j, config_info) in enumerate(block_info['configs']):
		if multirow_size % 27 == 0:
			if configs_left < 27:
				multirow_size = configs_left
			else:
				multirow_size = 27

			block_number_text = "\\multirow{" + str(multirow_size) + "}{*}{" + str(i + 1) + "} "
			block_diffs += block_number_text

		metric1 = config_info['metric1']
		metric2 = config_info['metric2']
		metric3 = config_info['metric3']

		block_diffs += " & " + str(j + 1) + \
			" & " + convert_to_rgb(block_info['metric1'], j + 1, 'mean', metric1['mean'], 2) + \
			" & " + convert_to_rgb(block_info['metric1'], j + 1, 'min', metric1['min'], 0) + \
			" & " + convert_to_rgb(block_info['metric1'], j + 1, 'max', metric1['max'], 0) + \
			" & " + convert_to_rgb(block_info['metric2'], j + 1, 'mean', metric2['mean'], 2) + \
			" & " + convert_to_rgb(block_info['metric2'], j + 1, 'min', metric2['min'], 0) + \
			" & " + convert_to_rgb(block_info['metric2'], j + 1, 'max', metric2['max'], 0) + \
			" & " + convert_to_rgb(block_info['metric3'], j + 1, 'mean', metric3['mean'], 2) + \
			" & " + convert_to_rgb(block_info['metric3'], j + 1, 'min', metric3['min'], 0) + \
			" & " + convert_to_rgb(block_info['metric3'], j + 1, 'max', metric3['max'], 0) + "\\\\\n"
		block_diffs += "\\tabucline{2-11}"

		configs_left -= 1
		multirow_size -= 1

	latex_rows += latex_table_multirow_template.replace('$3', block_diffs)

latex_document += latex_table_template.replace('$1', latex_rows).replace('$2', module_name + ", diferencias contra el Ground Truth (GT) en el conteo de personas, seg\\'un las tres m\\'etricas.")
latex_document += "\\end{document}\n"

with open(directory_of_results + "differences/latex_counter_diff_tables.tex", 'w') as out:
	out.write(latex_document)
