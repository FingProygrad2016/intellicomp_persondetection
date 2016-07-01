#!/usr/bin/python

import os
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

for file in os.listdir(directory_of_results + "histograms/data"):
    if file.endswith(".dat"):
        latex_document += latex_histogram_template.replace('$1', 'data/' + file).replace('$2', file.replace('.dat', '').replace('_', ' ').replace('-', ' '))

latex_document += "\\end{document}\n"

with open(directory_of_results + "histograms/latex_histograms.tex", 'w') as out:
	out.write(latex_document)