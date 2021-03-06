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
	if minimum == maximum:
		return start_point
	return float(Decimal(start_point) + Decimal(end_point - start_point)*Decimal(value - minimum)/Decimal(maximum - minimum))


def convert_to_rgb(min_max_values, config_number, module, val, precision):

	minval = min_max_values['min_values'][module]['value']
	maxval = min_max_values['max_values'][module]['value']

	opacity = int(transition(val, minval, maxval, 0, 100))

	number_formatter = "%."+str(precision)+"f"

	if opacity >= 45:
		return "\\color{white}{\\cellcolor{black!" + str(opacity) + "}{" + number_formatter % round(val, precision) + "}}"
	else:
		return "\\cellcolor{black!" + str(opacity) + "}{" + number_formatter % round(val, precision) + "}"



latex_table_template = """
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
	\\end{longtabu}
	\\end{landscape}
"""

latex_table_multirow_template = """
	$3 \\tabucline-
"""

latex_document = """
	\\documentclass{article}
	\\usepackage[utf8]{inputenc}

	\\usepackage{multirow}
	\\usepackage{longtable}
	\\usepackage{tabu}
	\\usepackage{lscape}
	\\usepackage{xcolor,colortbl}

	\\begin{document}
"""

csv_header_template = "Conf\t(mean)Personas.vs.GT\t(min)Personas.vs.GT\t(max)Personas.vs.GT\t(mean)Tracklets.vs.GT\t(min)Tracklets.vs.GT\t(max)Tracklets.vs.GT\t(mean)Interpolado.vs.GT\t(min)Interpolado.vs.GT\t(max)Interpolado.vs.GT\n"

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

		if len(blocks_info) < block_number:
			for i in range(0, block_number - len(blocks_info)):
				blocks_info.append({
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
				})

		block_info = blocks_info[block_number - 1]

		if len(block_info['configs']) < config_in_block:
			for i in range(0, config_in_block - len(block_info['configs'])):
				block_info['configs'].append({
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
				})

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
		
csv_files_text = []
latex_rows = ""

for (i, block_info) in enumerate(blocks_info):

	csv_file_text = csv_header_template

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

		metric1 = config_info['metric1']
		metric2 = config_info['metric2']
		metric3 = config_info['metric3']

		csv_file_text += str(j + 1) + \
			"\t" + "%.2f" % metric1['mean'] + "\t" + "%.0f" % metric1['min'] + "\t" + "%.0f" % metric1['max'] + \
			"\t" + "%.2f" % metric2['mean'] + "\t" + "%.0f" % metric2['min'] + "\t" + "%.0f" % metric2['max'] + \
			"\t" + "%.2f" % metric3['mean'] + "\t" + "%.0f" % metric3['min'] + "\t" + "%.0f" % metric3['max'] + "\n"

		if multirow_size % 27 == 0:
			if configs_left < 27:
				multirow_size = configs_left
			else:
				multirow_size = 27

			block_number_text = "\\multirow{" + str(multirow_size) + "}{*}{" + str(i + 1) + "} "
			block_diffs += block_number_text

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

	csv_files_text.append((i + 1, csv_file_text))

	latex_rows += latex_table_multirow_template.replace('$3', block_diffs)

latex_document += latex_table_template.replace('$1', latex_rows).replace('$2', module_name + ", diferencias contra el Ground Truth (GT) en el conteo de personas, seg\\'un las tres m\\'etricas.")
latex_document += "\\end{document}\n"

with open(directory_of_results + "differences/out/latex_counter_diff_tables.tex", 'w') as out:
	out.write(latex_document)

for (block_number, text) in csv_files_text:
	with open(directory_of_results + "differences/out/counter_diff_B" + "%02d" % block_number + ".csv", "w") as f:
		f.write(text)
