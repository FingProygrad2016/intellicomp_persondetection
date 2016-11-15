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
	print("must be: python get_times_latex_tables.py directory_of_results")
	exit()

def transition(value, minimum, maximum, start_point, end_point):
	if minimum < 0:
		maximum += -minimum
		value += -minimum
		minimum = 0
	if minimum == maximum:
		return start_point
	return float(Decimal(start_point) + Decimal(end_point - start_point)*Decimal(value - minimum)/Decimal(maximum - minimum))

def convert_to_rgb(min_max_values, config_number, module, val):
	minval = min_max_values['min_values'][module]['value']
	maxval = min_max_values['max_values'][module]['value']

	opacity = int(transition(val, minval, maxval, 0, 100))

	if opacity >= 45:
		return "\\color{white}{\\cellcolor{black!" + str(opacity) + "}{" + "%.5f" % round(val, 5) + "}}"
	else:
		return "\\cellcolor{black!" + str(opacity) + "}{" + "%.5f" % round(val, 5) + "}"

latex_table_template = """
	\\noindent\\begin{longtabu} to \\linewidth {c c | *{5}{@{ }c@{ }}}
	 & & & Detecci\\'on y & & & \\\\
	 & & Sustracci\\'on & clasificaci\\'on & Detecci\\'on & & \\\\
    Bloque & Conf & de fondo & de blobs & de personas & Seguimiento & Total \\\\
	\\tabucline-
	$1
	\\caption{$2}
	\\end{longtabu}
	% }
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
	\\usepackage{xcolor,colortbl}

	\\begin{document}
"""

csv_header_template = "Conf\tBS(avg)\tBS(max)\tBD(avg)\tBD(max)\tPD(avg)\tPD(max)\tT(avg)\tT(max)\tTot(avg)\tTot(max)\n"

blocks_info = []

module_block_config_matcher = re.compile('(.+?)-.*-B(\d+?)-(\d+)')

float_matcher = '[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?'
times_info_matcher_one = '.*?Background.*?('+float_matcher+').*?Blob.*?('+float_matcher+').*?Person.*?('+float_matcher+').*?Tracker.*?('+float_matcher+')'
times_info_matcher_both = re.compile(times_info_matcher_one + times_info_matcher_one)

infinite = 9999

module_name = None
for file in os.listdir(directory_of_results + "data"):
	if file.endswith(".txt"):
		mbc = module_block_config_matcher.match(file)
		module_name = mbc.group(1).replace('_', ' ')
		block_number = int(mbc.group(2))
		config_in_block = int(mbc.group(3))

		if len(blocks_info) < block_number:
			for i in range(0, block_number - len(blocks_info)):
				blocks_info.append({
					'average_times': {'min_values': {
										'BS': {'value': infinite, 'config': -1},
										'BD': {'value': infinite, 'config': -1},
										'PD': {'value': infinite, 'config': -1},
										'T': {'value': infinite, 'config': -1},
										'Tot': {'value': infinite, 'config': -1}
										},
										'max_values': {
											'BS': {'value': 0, 'config': -1},
											'BD': {'value': 0, 'config': -1},
											'PD': {'value': 0, 'config': -1},
											'T': {'value': 0, 'config': -1},
											'Tot': {'value': 0, 'config': -1}
										}},
					'max_times': {'min_values': {
									'BS': {'value': infinite, 'config': -1},
									'BD': {'value': infinite, 'config': -1},
									'PD': {'value': infinite, 'config': -1},
									'T': {'value': infinite, 'config': -1},
									'Tot': {'value': infinite, 'config': -1}
									},
									'max_values': {
										'BS': {'value': 0, 'config': -1},
										'BD': {'value': 0, 'config': -1},
										'PD': {'value': 0, 'config': -1},
										'T': {'value': 0, 'config': -1},
										'Tot': {'value': 0, 'config': -1}
									}},
					'configs': []
				})

		block_info = blocks_info[block_number - 1]

		if len(block_info['configs']) < config_in_block:
			for i in range(0, config_in_block - len(block_info['configs'])):
				block_info['configs'].append({
					'average_times': {
						'BS': 0,
						'BD': 0,
						'PD': 0,
						'T': 0,
						'Tot': 0
					},
					'max_times': {
						'BS': 0,
						'BD': 0,
						'PD': 0,
						'T': 0,
						'Tot': 0
					}
				})

		config_info = block_info['configs'][config_in_block - 1]

		f = open(directory_of_results + "data/" + file, "r")
		
		file_info = f.read()
		file_info = file_info.replace('\n', ' ').replace('\r', ' ')

		times = times_info_matcher_both.match(file_info)

		average_times = config_info['average_times']
		
		average_times['BS'] = float(times.group(1))
		if average_times['BS'] < block_info['average_times']['min_values']['BS']['value']:
			block_info['average_times']['min_values']['BS']['value'] = average_times['BS']
			block_info['average_times']['min_values']['BS']['config'] = config_in_block
		if average_times['BS'] > block_info['average_times']['max_values']['BS']['value']:
			block_info['average_times']['max_values']['BS']['value'] = average_times['BS']
			block_info['average_times']['max_values']['BS']['config'] = config_in_block
		
		average_times['BD'] = float(times.group(2))
		if average_times['BD'] < block_info['average_times']['min_values']['BD']['value']:
			block_info['average_times']['min_values']['BD']['value'] = average_times['BD']
			block_info['average_times']['min_values']['BD']['config'] = config_in_block
		if average_times['BD'] > block_info['average_times']['max_values']['BD']['value']:
			block_info['average_times']['max_values']['BD']['value'] = average_times['BD']
			block_info['average_times']['max_values']['BD']['config'] = config_in_block
		
		average_times['PD'] = float(times.group(3))
		if average_times['PD'] < block_info['average_times']['min_values']['PD']['value']:
			block_info['average_times']['min_values']['PD']['value'] = average_times['PD']
			block_info['average_times']['min_values']['PD']['config'] = config_in_block
		if average_times['PD'] > block_info['average_times']['max_values']['PD']['value']:
			block_info['average_times']['max_values']['PD']['value'] = average_times['PD']
			block_info['average_times']['max_values']['PD']['config'] = config_in_block
		
		average_times['T'] = float(times.group(4))
		if average_times['T'] < block_info['average_times']['min_values']['T']['value']:
			block_info['average_times']['min_values']['T']['value'] = average_times['T']
			block_info['average_times']['min_values']['T']['config'] = config_in_block
		if average_times['T'] > block_info['average_times']['max_values']['T']['value']:
			block_info['average_times']['max_values']['T']['value'] = average_times['T']
			block_info['average_times']['max_values']['T']['config'] = config_in_block
		
		average_times['Tot'] = average_times['BS'] + average_times['BD'] + average_times['PD'] + average_times['T']
		if average_times['Tot'] < block_info['average_times']['min_values']['Tot']['value']:
			block_info['average_times']['min_values']['Tot']['value'] = average_times['Tot']
			block_info['average_times']['min_values']['Tot']['config'] = config_in_block
		if average_times['Tot'] > block_info['average_times']['max_values']['Tot']['value']:
			block_info['average_times']['max_values']['Tot']['value'] = average_times['Tot']
			block_info['average_times']['max_values']['Tot']['config'] = config_in_block

		max_times = config_info['max_times']

		max_times['BS'] = float(times.group(5))
		if max_times['BS'] < block_info['max_times']['min_values']['BS']['value']:
			block_info['max_times']['min_values']['BS']['value'] = max_times['BS']
			block_info['max_times']['min_values']['BS']['config'] = config_in_block
		if max_times['BS'] > block_info['max_times']['max_values']['BS']['value']:
			block_info['max_times']['max_values']['BS']['value'] = max_times['BS']
			block_info['max_times']['max_values']['BS']['config'] = config_in_block

		max_times['BD'] = float(times.group(6))
		if max_times['BD'] < block_info['max_times']['min_values']['BD']['value']:
			block_info['max_times']['min_values']['BD']['value'] = max_times['BD']
			block_info['max_times']['min_values']['BD']['config'] = config_in_block
		if max_times['BD'] > block_info['max_times']['max_values']['BD']['value']:
			block_info['max_times']['max_values']['BD']['value'] = max_times['BD']
			block_info['max_times']['max_values']['BD']['config'] = config_in_block

		max_times['PD'] = float(times.group(7))
		if max_times['PD'] < block_info['max_times']['min_values']['PD']['value']:
			block_info['max_times']['min_values']['PD']['value'] = max_times['PD']
			block_info['max_times']['min_values']['PD']['config'] = config_in_block
		if max_times['PD'] > block_info['max_times']['max_values']['PD']['value']:
			block_info['max_times']['max_values']['PD']['value'] = max_times['PD']
			block_info['max_times']['max_values']['PD']['config'] = config_in_block

		max_times['T'] = float(times.group(8))
		if max_times['T'] < block_info['max_times']['min_values']['T']['value']:
			block_info['max_times']['min_values']['T']['value'] = max_times['T']
			block_info['max_times']['min_values']['T']['config'] = config_in_block
		if max_times['T'] > block_info['max_times']['max_values']['T']['value']:
			block_info['max_times']['max_values']['T']['value'] = max_times['T']
			block_info['max_times']['max_values']['T']['config'] = config_in_block

		max_times['Tot'] = max_times['BS'] + max_times['BD'] + max_times['PD'] + max_times['T']
		if max_times['Tot'] < block_info['max_times']['min_values']['Tot']['value']:
			block_info['max_times']['min_values']['Tot']['value'] = max_times['Tot']
			block_info['max_times']['min_values']['Tot']['config'] = config_in_block
		if max_times['Tot'] > block_info['max_times']['max_values']['Tot']['value']:
			block_info['max_times']['max_values']['Tot']['value'] = max_times['Tot']
			block_info['max_times']['max_values']['Tot']['config'] = config_in_block

csv_files_text = []
average_times_latex_rows = ""
max_times_latex_rows = ""

for (i, block_info) in enumerate(blocks_info):

	csv_file_text = csv_header_template

	block_average_times = ""
	block_max_times = ""

	block_average_times += " & " + "mejor" + \
		" & " + "%.5f" % block_info['average_times']['min_values']['BS']['value'] + \
		" & " + "%.5f" % block_info['average_times']['min_values']['BD']['value'] + \
		" & " + "%.5f" % block_info['average_times']['min_values']['PD']['value'] + \
		" & " + "%.5f" % block_info['average_times']['min_values']['T']['value'] + \
		" & " + "%.5f" % block_info['average_times']['min_values']['Tot']['value'] + "\\\\\n"

	block_average_times += " & " + "peor" + \
		" & " + "%.5f" % block_info['average_times']['max_values']['BS']['value'] + \
		" & " + "%.5f" % block_info['average_times']['max_values']['BD']['value'] + \
		" & " + "%.5f" % block_info['average_times']['max_values']['PD']['value'] + \
		" & " + "%.5f" % block_info['average_times']['max_values']['T']['value'] + \
		" & " + "%.5f" % block_info['average_times']['max_values']['Tot']['value'] + "\\\\\n"

	block_average_times += "\\tabucline{2-7}"
	block_average_times += "\\tabucline{2-7}"

	block_max_times += " & " + "mejor" + \
		" & " + "%.5f" % block_info['max_times']['min_values']['BS']['value'] + \
		" & " + "%.5f" % block_info['max_times']['min_values']['BD']['value'] + \
		" & " + "%.5f" % block_info['max_times']['min_values']['PD']['value'] + \
		" & " + "%.5f" % block_info['max_times']['min_values']['T']['value'] + \
		" & " + "%.5f" % block_info['max_times']['min_values']['Tot']['value'] + "\\\\\n"

	block_max_times += " & " + "peor" + \
		" & " + "%.5f" % block_info['max_times']['max_values']['BS']['value'] + \
		" & " + "%.5f" % block_info['max_times']['max_values']['BD']['value'] + \
		" & " + "%.5f" % block_info['max_times']['max_values']['PD']['value'] + \
		" & " + "%.5f" % block_info['max_times']['max_values']['T']['value'] + \
		" & " + "%.5f" % block_info['max_times']['max_values']['Tot']['value'] + "\\\\\n"

	block_max_times += "\\tabucline{2-7}"
	block_max_times += "\\tabucline{2-7}"

	configs_left = len(block_info['configs'])
	multirow_size = 27

	for (j, config_info) in enumerate(block_info['configs']):

		average_times = config_info['average_times']
		max_times = config_info['max_times']

		csv_file_text += str(j + 1) + \
			"\t" + "%.5f" % average_times['BS'] + "\t" + "%.5f" % max_times['BS'] + \
			"\t" + "%.5f" % average_times['BD'] + "\t" + "%.5f" % max_times['BD'] + \
			"\t" + "%.5f" % average_times['PD'] + "\t" + "%.5f" % max_times['PD'] + \
			"\t" + "%.5f" % average_times['T'] + "\t" + "%.5f" % max_times['T'] + \
			"\t" + "%.5f" % average_times['Tot'] + "\t" + "%.5f" % max_times['Tot'] + "\n"

		if multirow_size % 27 == 0:
			if configs_left < 27:
				multirow_size = configs_left
			else:
				multirow_size = 27

			block_number_text = "\\multirow{" + str(multirow_size) + "}{*}{" + str(i + 1) + "} "
			block_average_times += block_number_text
			block_max_times += block_number_text
		
		block_average_times += " & " + str(j + 1) + \
			" & " + convert_to_rgb(block_info['average_times'], j + 1, 'BS', average_times['BS']) + \
			" & " + convert_to_rgb(block_info['average_times'], j + 1, 'BD', average_times['BD']) + \
			" & " + convert_to_rgb(block_info['average_times'], j + 1, 'PD', average_times['PD']) + \
			" & " + convert_to_rgb(block_info['average_times'], j + 1, 'T', average_times['T']) + \
			" & " + convert_to_rgb(block_info['average_times'], j + 1, 'Tot', average_times['Tot']) + "\\\\\n"
		block_average_times += "\\tabucline{2-7}"

		block_max_times += " & " + str(j + 1) + \
			" & " + convert_to_rgb(block_info['max_times'], j + 1, 'BS', max_times['BS']) + \
			" & " + convert_to_rgb(block_info['max_times'], j + 1, 'BD', max_times['BD']) + \
			" & " + convert_to_rgb(block_info['max_times'], j + 1, 'PD', max_times['PD']) + \
			" & " + convert_to_rgb(block_info['max_times'], j + 1, 'T', max_times['T']) + \
			" & " + convert_to_rgb(block_info['max_times'], j + 1, 'Tot', max_times['Tot']) + "\\\\\n"
		block_max_times += "\\tabucline{2-7}"

		configs_left -= 1
		multirow_size -= 1

	csv_files_text.append((i + 1, csv_file_text))

	average_times_latex_rows += latex_table_multirow_template.replace('$3', block_average_times)
	max_times_latex_rows += latex_table_multirow_template.replace('$3', block_max_times)

latex_document += latex_table_template.replace('$1', average_times_latex_rows).replace('$2', module_name + ", tiempos promedio de procesamiento por frame.")
latex_document += latex_table_template.replace('$1', max_times_latex_rows).replace('$2', module_name + ", tiempos m\\'aximos de procesamiento por frame.")
latex_document += "\\end{document}\n"

with open(directory_of_results + "out/latex_times_tables.tex", 'w') as out:
	out.write(latex_document)

for (block_number, text) in csv_files_text:
	with open(directory_of_results + "out/times_B" + "%02d" % block_number + ".csv", "w") as f:
		f.write(text)
