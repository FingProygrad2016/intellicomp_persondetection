#!/usr/bin/python3

import os
import re
from sys import argv

if len(argv) == 2:
    directory_of_results = argv[1]
else:
	print("must be: python get_counters_latex_histograms.py directory_of_results")
	exit()

latex_histogram_template = """
	\\pgfplotstableread{$1}{\\datatable}
	\\begin{figure}
		\\centering
		\\begin{tikzpicture}
			\\begin{axis}[
				ybar=2*\\pgflinewidth,
				xlabel=Diferencia,
				ylabel=Cantidad de frames,
				ymin=0,
				xmin=0,
				xtick=data,
				enlarge x limits=0.09,
				%tickwidth=0pt,
				x=1.5cm],
			\\addplot +[] table [x={diff}, y={metric_1}] {\\datatable};
			\\addplot +[] table [x={diff}, y={metric_2}] {\\datatable};
			\\addplot +[] table [x={diff}, y={metric_3}] {\\datatable};
			\\legend{m\\'etrica 1, m\\'etrica 2, m\\'etrica 3}
			\\end{axis}
		\\end{tikzpicture}
		\\caption{$2}
	\\end{figure}
"""

latex_document = """
	\\documentclass{article}
	\\usepackage[utf8]{inputenc}

	\\usepackage{pgfplots}
	\\pgfplotsset{compat=1.5}% <-- moves axis labels near ticklabels (respects tick label widths)
	
	\\begin{document}
"""

module_block_config_matcher = re.compile('(.+?)-.*-B(\d+?)-(\d+)')

for file in os.listdir(directory_of_results + "histograms/data"):
	if file.endswith(".dat"):
		m = module_block_config_matcher.match(file)
		module_name = m.group(1).replace('_', ' ')
		block_number = m.group(2)
		config_in_block = m.group(3)
		latex_document += latex_histogram_template.replace('$1', 'data/' + file).replace('$2', module_name + ', bloque ' + str(block_number) + ', configuraci\\\'on ' + str(config_in_block))

latex_document += "\\end{document}\n"

with open(directory_of_results + "histograms/latex_histograms.tex", 'w') as out:
	out.write(latex_document)
