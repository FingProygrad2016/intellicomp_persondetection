#!/usr/bin/python3

import os
import re
from sys import argv

if len(argv) == 2:
    directory_of_results = argv[1]
else:
	print("must be: python get_counters_latex_tables.py directory_of_results")
	exit()

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

	latex_rows += latex_table_multirow_template.replace('$1', str(len(block_info))).replace('$2', str(i + 1)).replace('$3', block_diffs)

latex_document += latex_table_template.replace('$1', latex_rows).replace('$2', module_name + ", diferencias contra el Ground Truth (GT) en el conteo de personas, seg\\'un las tres m\\'etricas.")
latex_document += "\\end{document}\n"

with open(directory_of_results + "differences/latex_counter_diff_tables.tex", 'w') as out:
	out.write(latex_document)
