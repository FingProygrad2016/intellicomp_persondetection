#!/usr/bin/python3

import os
import re
from sys import argv

if len(argv) == 2:
    directory_of_results = argv[1]
else:
	print("must be: python get_times_latex_tables.py directory_of_results")
	exit()

latex_table_template = """
	{\\renewcommand{\\arraystretch}{1.2}
	\\begin{table}
	\\begin{tabular}{c c *{5}{@{ }c@{ }}}
	Bloque & Configuraci\\'on & 
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
times_info_matcher_one = '.*?Background.*?('+float_matcher+').*?Blob.*?('+float_matcher+').*?Person.*?('+float_matcher+').*?Tracker.*?('+float_matcher+').*?Total.*?('+float_matcher+')'
times_info_matcher_both = re.compile(times_info_matcher_one + times_info_matcher_one)

module_name = None
for file in os.listdir(directory_of_results + "data"):
	if file.endswith(".txt"):
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
				block_info.append(["", ""])

		f = open(directory_of_results + "data/" + file, "r")
		
		file_info = f.read()
		file_info = file_info.replace('\n', ' ').replace('\r', ' ')

		times = times_info_matcher_both.match(file_info)

		# Average times info
		block_info[config_in_block - 1][0] = " & " + str(config_in_block) + \
			" & " + "%.5f" % round(float(times.group(1)),5) + " & " + "%.5f" % round(float(times.group(2)),5) + " & " + "%.5f" % round(float(times.group(3)),5) + \
			" & " + "%.5f" % round(float(times.group(4)),5) + " & " + "%.5f" % round(float(times.group(5)),5) + "\\\\\n"

		# Max times info
		block_info[config_in_block - 1][1] = " & " + str(config_in_block) + \
			" & " + "%.5f" % round(float(times.group(6)),5) + " & " + "%.5f" % round(float(times.group(7)),5) + " & " + "%.5f" % round(float(times.group(8)),5) + \
			" & " + "%.5f" % round(float(times.group(9)),5) + " & " + "%.5f" % round(float(times.group(10)),5) + "\\\\\n"

average_times_latex_rows = ""
max_times_latex_rows = ""

for (i, block_info) in enumerate(blocks_info):
	block_average_times = ""
	block_max_times = ""
	for (j, config_info) in enumerate(block_info):
		block_average_times += config_info[0]
		block_max_times += config_info[1]
	average_times_latex_rows += latex_table_multirow_template.replace('$1', str(len(block_info))).replace('$2', str(i + 1)).replace('$3', block_average_times)
	max_times_latex_rows += latex_table_multirow_template.replace('$1', str(len(block_info))).replace('$2', str(i + 1)).replace('$3', block_max_times)

latex_document += latex_table_template.replace('$1', average_times_latex_rows).replace('$2', module_name + ", tiempos promedio.")
latex_document += latex_table_template.replace('$1', max_times_latex_rows).replace('$2', module_name + ", tiempos m\\'aximos.")
latex_document += "\\end{document}\n"

with open(directory_of_results + "latex_times_tables.tex", 'w') as out:
	out.write(latex_document)
