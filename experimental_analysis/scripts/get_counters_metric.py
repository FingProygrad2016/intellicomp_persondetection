#!/usr/bin/python3

from sys import argv

gt_counter_path = "../ground_truth/gt_counter.txt"
result_counter_path = ""

if len(argv) == 4:
    result_counter_path = argv[1]
    result_counter_filename = argv[2]
    directory_for_results = argv[3]
else:
	print("must be: python get_counters_metric.py file_path/file_name file_name directory_for_results")
	exit()

infinite = 9999

histogram = [] # [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

one_statistic = {
	'name': '',
	'min_diff': infinite,
	'max_diff': 0,
	'mean_diff': 0,
	'histogram': None
}

statistics = []

one_statistic.update({'name': 'Current persons', 'histogram': histogram.copy()})
statistics.append(one_statistic.copy())
one_statistic.update({'name': 'Current tracklets', 'histogram': histogram.copy()})
statistics.append(one_statistic.copy())
one_statistic.update({'name': 'Current tracklets/persons interpol. num', 'histogram': histogram.copy()})
statistics.append(one_statistic.copy())

gt_file = open(gt_counter_path, 'r')
res_file = open(result_counter_path, 'r')

gt_file_lines = gt_file.readlines()
res_file_lines = res_file.readlines()

# jump over title line and blank line
res_file_lines = res_file_lines[2:]

# first gt data line
gt_dataline = gt_file_lines[0].split(",")
# first res data line
res_dataline = res_file_lines[0].split(",")

if gt_dataline[0] != res_dataline[0]:
	print("first frame in \"", result_counter_path, "\" is not ", gt_dataline[0], "\n")
	exit()

for i in range(0, len(gt_file_lines)):
	gt_dataline = gt_file_lines[i].split(",")
	res_dataline = res_file_lines[i].split(",")

	gt_curr_persons = int(gt_dataline[1])

	weight_of_curr_diff = 1/(i+1)
	weight_of_prev_mean_diff = 1 - weight_of_curr_diff

	for j in range(0, 3):
		diff = abs(int(res_dataline[j+1]) - gt_curr_persons)

		statistic = statistics[j]

		if diff < statistic['min_diff']:
			statistic['min_diff'] = diff
		if diff > statistic['max_diff']:
			statistic['max_diff'] = diff
		statistic['mean_diff'] = statistic['mean_diff'] * weight_of_prev_mean_diff + \
			diff * weight_of_curr_diff

		histogram = statistic['histogram']
		if len(histogram) <= diff:
			for k in range(0, diff - (len(histogram) - 1)):
				for l in range(0, 3):
					statistics[l]['histogram'].append(0)
		histogram[diff] += 1

with open(directory_for_results + "differences/" + result_counter_filename + '_diff.txt', 'w') as out:
	for i in range(0, 3):
		out.write(statistics[i]['name']+" (mean, min, max): "+"%.2f" % round(statistics[i]['mean_diff'],2)+", "+str(statistics[i]['min_diff'])+", "+str(statistics[i]['max_diff'])+"\n")

with open(directory_for_results + "histograms/data/" + result_counter_filename + '_diff-histogram.dat', 'w') as out:
	histograms_length = len(statistics[0]['histogram'])
	out.write('diff\tmetric_1\tmetric_2\tmetric_3\n')
	for i in range(0, histograms_length):
		out.write(str(i))
		for j in range(0, 3):
			out.write("\t" + str(statistics[j]['histogram'][i]))
		out.write("\n")

