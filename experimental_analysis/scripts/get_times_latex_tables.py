#!/usr/bin/python3

import os
import re
from sys import argv

if len(argv) == 2:
    directory_of_results = argv[1]
else:
	print("must be: python get_times_latex_tables.py directory_of_results")
	exit()

colors = [(0, 255, 0), (255, 0, 0)]

def convert_to_rgb(minval, maxval, val):
	print("minval: ", str(minval), '; maxval: ', str(maxval), '; val: ', str(val))
	max_index = len(colors)-1
	v = float(val-minval) / float(maxval-minval) * max_index
	i1, i2 = int(v), min(int(v)+1, max_index)
	(r1, g1, b1), (r2, g2, b2) = colors[i1], colors[i2]
	f = v - i1
	return "\cellcolor{rgb:red," + str(int(r1 + f*(r2-r1))) + ";green," + str(int(g1 + f*(g2-g1))) + ";blue," + str(int(b1 + f*(b2-b1))) + "}"

latex_table_template = """
	{\\renewcommand{\\arraystretch}{1.2}
	\\begin{table}
	\\begin{tabular}{c c | *{5}{@{ }c@{ }}}
	Bloque & Conf & 
	\\begin{tabular}{c}Sustracci\\'on\\\\de fondo\\end{tabular} & 
	\\begin{tabular}{c}Detecci\\'on y\\\\clasificaci\\'on\\\\de blobs\\end{tabular} & 
	\\begin{tabular}{c}Detecci\\'on\\\\de personas\\end{tabular} & 
	\\begin{tabular}{c}Seguimiento\\end{tabular} & 
	\\begin{tabular}{c}Total\\end{tabular} \\\\
	\\hline
	$1
	\\end{tabular}
	\\caption{$2}
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
times_info_matcher_one = '.*?Background.*?('+float_matcher+').*?Blob.*?('+float_matcher+').*?Person.*?('+float_matcher+').*?Tracker.*?('+float_matcher+')'
times_info_matcher_both = re.compile(times_info_matcher_one + times_info_matcher_one)

infinite = 9999
min_values_template = {
	'BS': infinite,
	'BD': infinite,
	'PD': infinite,
	'T': infinite,
	'Tot': infinite,
}
max_values_template = {
	'BS': 0,
	'BD': 0,
	'PD': 0,
	'T': 0,
	'Tot': 0,
}
block_info_template = {
	'average_times': {'min_values': min_values_template.copy(), 'max_values': max_values_template.copy()},
	'max_times': {'min_values': min_values_template.copy(), 'max_values': max_values_template.copy()},
	'configs': []
}
config_template = {
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
}

module_name = None
for file in os.listdir(directory_of_results + "data"):
	if file.endswith(".txt"):
		mbc = module_block_config_matcher.match(file)
		module_name = mbc.group(1).replace('_', ' ')
		block_number = int(mbc.group(2))
		config_in_block = int(mbc.group(3))

		if len(blocks_info) < block_number:
			for i in range(0, block_number - len(blocks_info)):
				blocks_info.append(block_info_template.copy())

		block_info = blocks_info[block_number - 1]

		if len(block_info['configs']) < config_in_block:
			for i in range(0, config_in_block - len(block_info['configs'])):
				block_info['configs'].append(config_template.copy())

		config_info = block_info['configs'][config_in_block - 1]

		f = open(directory_of_results + "data/" + file, "r")
		
		file_info = f.read()
		file_info = file_info.replace('\n', ' ').replace('\r', ' ')

		times = times_info_matcher_both.match(file_info)

		average_times = config_info['average_times']
		
		average_times['BS'] = float(times.group(1))
		if average_times['BS'] < block_info['average_times']['min_values']['BS']:
			block_info['average_times']['min_values']['BS'] = average_times['BS']
		if average_times['BS'] > block_info['average_times']['max_values']['BS']:
			block_info['average_times']['max_values']['BS'] = average_times['BS']
		average_times['BD'] = float(times.group(2))
		if average_times['BD'] < block_info['average_times']['min_values']['BD']:
			block_info['average_times']['min_values']['BD'] = average_times['BD']
		if average_times['BD'] > block_info['average_times']['max_values']['BD']:
			block_info['average_times']['max_values']['BD'] = average_times['BD']
		average_times['PD'] = float(times.group(3))
		if average_times['PD'] < block_info['average_times']['min_values']['PD']:
			block_info['average_times']['min_values']['PD'] = average_times['PD']
		if average_times['PD'] > block_info['average_times']['max_values']['PD']:
			block_info['average_times']['max_values']['PD'] = average_times['PD']
		average_times['T'] = float(times.group(4))
		if average_times['T'] < block_info['average_times']['min_values']['T']:
			block_info['average_times']['min_values']['T'] = average_times['T']
		if average_times['T'] > block_info['average_times']['max_values']['T']:
			block_info['average_times']['max_values']['T'] = average_times['T']
		average_times['Tot'] = average_times['BS'] + average_times['BD'] + average_times['PD'] + average_times['T']
		if average_times['Tot'] < block_info['average_times']['min_values']['Tot']:
			block_info['average_times']['min_values']['Tot'] = average_times['Tot']
		if average_times['Tot'] > block_info['average_times']['max_values']['Tot']:
			block_info['average_times']['max_values']['Tot'] = average_times['Tot']

		max_times = config_info['max_times']

		max_times['BS'] = float(times.group(5))
		if max_times['BS'] < block_info['max_times']['min_values']['BS']:
			block_info['max_times']['min_values']['BS'] = max_times['BS']
		if max_times['BS'] > block_info['max_times']['max_values']['BS']:
			block_info['max_times']['max_values']['BS'] = max_times['BS']
		max_times['BD'] = float(times.group(6))
		if max_times['BD'] < block_info['max_times']['min_values']['BD']:
			block_info['max_times']['min_values']['BD'] = max_times['BD']
		if max_times['BD'] > block_info['max_times']['max_values']['BD']:
			block_info['max_times']['max_values']['BD'] = max_times['BD']
		max_times['PD'] = float(times.group(7))
		if max_times['PD'] < block_info['max_times']['min_values']['PD']:
			block_info['max_times']['min_values']['PD'] = max_times['PD']
		if max_times['PD'] > block_info['max_times']['max_values']['PD']:
			block_info['max_times']['max_values']['PD'] = max_times['PD']
		max_times['T'] = float(times.group(8))
		if max_times['T'] < block_info['max_times']['min_values']['T']:
			block_info['max_times']['min_values']['T'] = max_times['T']
		if max_times['T'] > block_info['max_times']['max_values']['T']:
			block_info['max_times']['max_values']['T'] = max_times['T']
		max_times['Tot'] = max_times['BS'] + max_times['BD'] + max_times['PD'] + max_times['T']
		if max_times['Tot'] < block_info['max_times']['min_values']['Tot']:
			block_info['max_times']['min_values']['Tot'] = max_times['Tot']
		if max_times['Tot'] > block_info['max_times']['max_values']['Tot']:
			block_info['max_times']['max_values']['Tot'] = max_times['Tot']

average_times_latex_rows = ""
max_times_latex_rows = ""

for (i, block_info) in enumerate(blocks_info):
	block_average_times = ""
	block_max_times = ""
	for (j, config_info) in enumerate(block_info['configs']):
		average_times = config_info['average_times']
		block_average_times += " & " + str(j + 1) + \
			" & " + convert_to_rgb(block_info['average_times']['min_values']['BS'], block_info['average_times']['max_values']['BS'], average_times['BS']) + "%.5f" % round(average_times['BS'],5) + \
			" & " + convert_to_rgb(block_info['average_times']['min_values']['BD'], block_info['average_times']['max_values']['BD'], average_times['BD']) + "%.5f" % round(average_times['BD'],5) + \
			" & " + convert_to_rgb(block_info['average_times']['min_values']['PD'], block_info['average_times']['max_values']['PD'], average_times['PD']) + "%.5f" % round(average_times['PD'],5) + \
			" & " + convert_to_rgb(block_info['average_times']['min_values']['T'], block_info['average_times']['max_values']['T'], average_times['T']) + "%.5f" % round(average_times['T'],5) + \
			" & " + convert_to_rgb(block_info['average_times']['min_values']['Tot'], block_info['average_times']['max_values']['Tot'], average_times['Tot']) + "%.5f" % round(average_times['Tot'],5) + "\\\\\n"

		max_times = config_info['max_times']
		block_max_times += " & " + str(j + 1) + \
			" & " + convert_to_rgb(block_info['max_times']['min_values']['BS'], block_info['max_times']['max_values']['BS'], max_times['BS']) + "%.5f" % round(max_times['BS'],5) + \
			" & " + convert_to_rgb(block_info['max_times']['min_values']['BD'], block_info['max_times']['max_values']['BD'], max_times['BD']) + "%.5f" % round(max_times['BD'],5) + \
			" & " + convert_to_rgb(block_info['max_times']['min_values']['PD'], block_info['max_times']['max_values']['PD'], max_times['PD']) + "%.5f" % round(max_times['PD'],5) + \
			" & " + convert_to_rgb(block_info['max_times']['min_values']['T'], block_info['max_times']['max_values']['T'], max_times['T']) + "%.5f" % round(max_times['T'],5) + \
			" & " + convert_to_rgb(block_info['max_times']['min_values']['Tot'], block_info['max_times']['max_values']['Tot'], max_times['Tot']) + "%.5f" % round(max_times['Tot'],5) + "\\\\\n"

	average_times_latex_rows += latex_table_multirow_template.replace('$1', str(len(block_info))).replace('$2', str(i + 1)).replace('$3', block_average_times)
	max_times_latex_rows += latex_table_multirow_template.replace('$1', str(len(block_info))).replace('$2', str(i + 1)).replace('$3', block_max_times)

latex_document += latex_table_template.replace('$1', average_times_latex_rows).replace('$2', module_name + ", tiempos promedio de procesamiento por frame.")
latex_document += latex_table_template.replace('$1', max_times_latex_rows).replace('$2', module_name + ", tiempos m\\'aximos de procesamiento por frame.")
latex_document += "\\end{document}\n"

with open(directory_of_results + "latex_times_tables.tex", 'w') as out:
	out.write(latex_document)
