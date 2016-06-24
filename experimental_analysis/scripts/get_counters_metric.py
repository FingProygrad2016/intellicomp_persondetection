#!/usr/bin/python

from sys import argv

gt_counter_path = "../ground_truth/gt_counter.txt"
result_counter_path = ""

if len(argv) == 3:
    result_counter_path = argv[1]
    result_counter_filename = argv[2]
else:
	print("must be: python get_counters_metric.py file_path/file_name file_name")
	exit()

infinite = 9999

curr_persons = {
	'min_diff': infinite,
	'max_diff': 0,
	'mean_diff': 0
}
curr_tracklets = {
	'min_diff': infinite,
	'max_diff': 0,
	'mean_diff': 0
}
curr_tracklets_over_persons_interp = {
	'min_diff': infinite,
	'max_diff': 0,
	'mean_diff': 0
}

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

	res_curr_persons = int(res_dataline[1])
	res_curr_tracklets = int(res_dataline[2])
	res_curr_tracklets_over_persons_interp = int(res_dataline[3])

	curr_persons_diff = abs(res_curr_persons - gt_curr_persons)
	curr_tracklets_diff = abs(res_curr_tracklets - gt_curr_persons)
	curr_tracklets_over_persons_interp_diff = \
		abs(res_curr_tracklets_over_persons_interp - gt_curr_persons)

	weight_of_curr_diff = 1/(i+1)
	weight_of_prev_mean_diff = 1 - weight_of_curr_diff

	if curr_persons_diff < curr_persons['min_diff']:
		curr_persons['min_diff'] = curr_persons_diff
	if curr_persons_diff > curr_persons['max_diff']:
		curr_persons['max_diff'] = curr_persons_diff
	curr_persons['mean_diff'] = curr_persons['mean_diff'] * weight_of_prev_mean_diff + \
		curr_persons_diff * weight_of_curr_diff

	if curr_tracklets_diff < curr_tracklets['min_diff']:
		curr_tracklets['min_diff'] = curr_tracklets_diff
	if curr_tracklets_diff > curr_tracklets['max_diff']:
		curr_tracklets['max_diff'] = curr_tracklets_diff
	curr_tracklets['mean_diff'] = curr_tracklets['mean_diff'] * weight_of_prev_mean_diff + \
		curr_tracklets_diff * weight_of_curr_diff

	if curr_tracklets_over_persons_interp_diff < curr_tracklets_over_persons_interp['min_diff']:
		curr_tracklets_over_persons_interp['min_diff'] = curr_tracklets_over_persons_interp_diff
	if curr_tracklets_over_persons_interp_diff > curr_tracklets_over_persons_interp['max_diff']:
		curr_tracklets_over_persons_interp['max_diff'] = curr_tracklets_over_persons_interp_diff
	curr_tracklets_over_persons_interp['mean_diff'] = \
		curr_tracklets_over_persons_interp['mean_diff'] * weight_of_prev_mean_diff + \
		curr_tracklets_over_persons_interp_diff * weight_of_curr_diff

with open('../processed_results/' + result_counter_filename + '_diff.txt', 'w') as out:
  out.write("Current persons detected (mean, min, max); Current tracklets (mean, min, max); Current tracklets/persons interpol. num (mean, min, max)\n\n")
  out.write("%.1f" % round(curr_persons['mean_diff'],1)+","+str(curr_persons['min_diff'])+","+str(curr_persons['max_diff'])+";")
  out.write("%.1f" % round(curr_tracklets['mean_diff'],1)+","+str(curr_tracklets['min_diff'])+","+str(curr_tracklets['max_diff'])+";")
  out.write("%.1f" % round(curr_tracklets_over_persons_interp['mean_diff'],1)+","+str(curr_tracklets_over_persons_interp['min_diff'])+","+str(curr_tracklets_over_persons_interp['max_diff']))
