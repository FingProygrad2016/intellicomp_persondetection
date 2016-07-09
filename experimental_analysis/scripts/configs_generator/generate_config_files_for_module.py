#!/usr/bin/python3

import os
import re
import itertools
from sys import argv

if len(argv) == 2:
    config_creator_file = './in_files/conf_creators/' + argv[1] + '.creator'
else:
	print("must be: python generate_config_files_for_module.py config_creator_name")
	exit()

f = open(config_creator_file)
all_text = f.read()

# turns: 'Tracking\n##\ntracking_base.conf\n##\nUSE_HISTOGRAMS_FOR_TRACKING;HISTOGRAM_COMPARISON_METHOD;PRIMARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS\n:[False][#][0, 0, 1]\n:[True][CORRELATION;CHI_SQUARED;CHI_SQUARED_ALT;INTERSECTION;HELLINGER;KL_DIV;EUCLIDEAN;MANHATTAN;CHEBYSEV][0, 0, 1]\n![mejor de los anteriores][mejor de los anteriores][1, 0, 0;0, 1, 0;0, 0, 1;0.5, 0.25, 0.25;0.25, 0.5, 0.25;0.25, 0.25, 0.5;0.33, 0.34, 0.33]\n##\nMAX_SECONDS_WITHOUT_UPDATE\n:[1;2;4;8]\n##\nMAX_SECONDS_TO_PREDICT_POSITION{(smaller than seconds without update [one on one])}\n:[0.5;1;2;4]\n##\nMAX_SECONDS_WITHOUT_ANY_BLOB{(smaller than seconds without update [one on one])}\n:[0;0.5;1.5;3.5]\n##\nMIN_SECONDS_TO_BE_ACCEPTED_IN_GROUP\n:[0;0.5;1.5;3.5]\n##\nKALMAN_FILTER_TYPE;KALMAN_FILTER_SMOOTH_LAG\n:[NORMAL][#]\n:[SMOOTHED][0;3{(FPS / 2)};7{(FPS)};14{(FPS * 2)}]\n##'
all_blocks_matcher = re.compile(r"([\s\S]+?)##")
all_blocks = all_blocks_matcher.findall(all_text)
# in: ['Tracking\n', '\ntracking_base.conf\n', '\nUSE_HISTOGRAMS_FOR_TRACKING;HISTOGRAM_COMPARISON_METHOD;PRIMARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS\n:[False][#][0, 0, 1]\n:[True][CORRELATION;CHI_SQUARED;CHI_SQUARED_ALT;INTERSECTION;HELLINGER;KL_DIV;EUCLIDEAN;MANHATTAN;CHEBYSEV][0, 0, 1]\n![mejor de los anteriores][mejor de los anteriores][1, 0, 0;0, 1, 0;0, 0, 1;0.5, 0.25, 0.25;0.25, 0.5, 0.25;0.25, 0.25, 0.5;0.33, 0.34, 0.33]\n', '\nMAX_SECONDS_WITHOUT_UPDATE\n:[1;2;4;8]\n', '\nMAX_SECONDS_TO_PREDICT_POSITION{(smaller than seconds without update [one on one])}\n:[0.5;1;2;4]\n', '\nMAX_SECONDS_WITHOUT_ANY_BLOB{(smaller than seconds without update [one on one])}\n:[0;0.5;1.5;3.5]\n', '\nMIN_SECONDS_TO_BE_ACCEPTED_IN_GROUP\n:[0;0.5;1.5;3.5]\n', '\nKALMAN_FILTER_TYPE;KALMAN_FILTER_SMOOTH_LAG\n:[NORMAL][#]\n:[SMOOTHED][0;3{(FPS / 2)};7{(FPS)};14{(FPS * 2)}]\n']

module_name = all_blocks[0].replace('\n','').replace('\r','').replace(' ', '_')
base_config_file = all_blocks[1].replace('\n','').replace('\r','')

result_conf_files_path = './out_files/conf_files/' + module_name + '/'
result_execution_plan_file = './out_files/execution_plan/' + module_name + '.execution_plan'

if not os.path.exists(result_conf_files_path):
    os.makedirs(result_conf_files_path)

string_variables_names_matcher = re.compile(r"^([^:!].+)")
divide_string_variables_names_matcher = re.compile(r"[\n\r;]([^\n\r;]+)")
block_string_config_creators_matcher = re.compile(r"([:!].+)")
divide_string_config_creator_matcher = re.compile(r"(\[.+?\])")
string_variable_possibilities_to_array_matcher = re.compile(r"[^\[;\]]+")

blocks_info = []
for i in range(2, len(all_blocks)):

	block_i = all_blocks[i]

	block_info = {}

	# turns: '\nUSE_HISTOGRAMS_FOR_TRACKING;HISTOGRAM_COMPARISON_METHOD;PRIMARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS\n:[False][#][0, 0, 1]\n:[True][CORRELATION;CHI_SQUARED;CHI_SQUARED_ALT;INTERSECTION;HELLINGER;KL_DIV;EUCLIDEAN;MANHATTAN;CHEBYSEV][0, 0, 1]\n![mejor de los anteriores][mejor de los anteriores][1, 0, 0;0, 1, 0;0, 0, 1;0.5, 0.25, 0.25;0.25, 0.5, 0.25;0.25, 0.25, 0.5;0.33, 0.34, 0.33]\n'
	block_i_string_variables_names = string_variables_names_matcher.findall(block_i)
	# in: ['\nUSE_HISTOGRAMS_FOR_TRACKING;HISTOGRAM_COMPARISON_METHOD;PRIMARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS']

	# turns: '\nUSE_HISTOGRAMS_FOR_TRACKING;HISTOGRAM_COMPARISON_METHOD;PRIMARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS'
	block_info['variables_names'] = divide_string_variables_names_matcher.findall(block_i_string_variables_names[0])
	# in: ['USE_HISTOGRAMS_FOR_TRACKING', 'HISTOGRAM_COMPARISON_METHOD', 'PRIMARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS']

	# turns: '\nUSE_HISTOGRAMS_FOR_TRACKING;HISTOGRAM_COMPARISON_METHOD;PRIMARY_HUNG_ALG_COMPARISON_METHOD_WEIGHTS\n:[False][#][0, 0, 1]\n:[True][CORRELATION;CHI_SQUARED;CHI_SQUARED_ALT;INTERSECTION;HELLINGER;KL_DIV;EUCLIDEAN;MANHATTAN;CHEBYSEV][0, 0, 1]\n![mejor de los anteriores][mejor de los anteriores][1, 0, 0;0, 1, 0;0, 0, 1;0.5, 0.25, 0.25;0.25, 0.5, 0.25;0.25, 0.25, 0.5;0.33, 0.34, 0.33]\n'
	block_i_string_config_creators = block_string_config_creators_matcher.findall(block_i)
	# in: [':[False][#][0, 0, 1]', ':[True][CORRELATION;CHI_SQUARED;CHI_SQUARED_ALT;INTERSECTION;HELLINGER;KL_DIV;EUCLIDEAN;MANHATTAN;CHEBYSEV][0, 0, 1]', '![mejor de los anteriores][mejor de los anteriores][1, 0, 0;0, 1, 0;0, 0, 1;0.5, 0.25, 0.25;0.25, 0.5, 0.25;0.25, 0.25, 0.5;0.33, 0.34, 0.33]']

	block_i_configs = []
	for j in range(0, len(block_i_string_config_creators)):
		string_config_creator_j = block_i_string_config_creators[j]

		block_config = {}
		block_config['is_executable'] = string_config_creator_j[0] == ':'

		string_config_creator_j = string_config_creator_j[1:]

		# turns: '[True][CORRELATION;CHI_SQUARED;CHI_SQUARED_ALT;INTERSECTION;HELLINGER;KL_DIV;EUCLIDEAN;MANHATTAN;CHEBYSEV][0, 0, 1]'
		string_variables_possibilities_config_creator_j = divide_string_config_creator_matcher.findall(string_config_creator_j)
		# in: ['[True]', '[CORRELATION;CHI_SQUARED;CHI_SQUARED_ALT;INTERSECTION;HELLINGER;KL_DIV;EUCLIDEAN;MANHATTAN;CHEBYSEV]', '[0, 0, 1]']

		variables_possibilities_config_creator_j = []
		for k in range(0, len(string_variables_possibilities_config_creator_j)):
			string_variable_possibilities_k = string_variables_possibilities_config_creator_j[k]

			# turns: '[CORRELATION;CHI_SQUARED;CHI_SQUARED_ALT;INTERSECTION;HELLINGER;KL_DIV;EUCLIDEAN;MANHATTAN;CHEBYSEV]'
			variable_possibilities_k = string_variable_possibilities_to_array_matcher.findall(string_variable_possibilities_k)
			# in: ['CORRELATION', 'CHI_SQUARED', 'CHI_SQUARED_ALT', 'INTERSECTION', 'HELLINGER', 'KL_DIV', 'EUCLIDEAN', 'MANHATTAN', 'CHEBYSEV']

			variables_possibilities_config_creator_j.append(variable_possibilities_k.copy())


		block_config['configuration'] = list(itertools.product(*variables_possibilities_config_creator_j))

		block_i_configs.append(block_config)

	block_info['configurations'] = block_i_configs

	blocks_info.append(block_info.copy())


f = open('./in_files/base_configurations/' + base_config_file)
base_text = f.read()

extra_text_matcher = re.compile("{.*}")

text_for_execution_plan = ''
for i in range(0, len(blocks_info)):

	block_info = blocks_info[i]

	block_number = i + 1

	text_for_execution_plan += 'Bloque ' + str(block_number) + '\n'
	
	variables_substitution_matchers = []

	text_for_execution_plan += 'Configuración\t'
	variables_count = len(block_info['variables_names'])
	for j in range(0, variables_count):
		variable_name = block_info['variables_names'][j]
		matcher = re.compile(r"(\n" + extra_text_matcher.sub('', variable_name) + "\s*=\s*).*(\n)")
		variables_substitution_matchers.append(matcher)
		text_for_execution_plan += variable_name.replace('{', ' ').replace('}', ' ') + '\t'
	text_for_execution_plan = text_for_execution_plan[:-1] + '\n'

	configurations = block_info['configurations']
	config_number_in_block = 1

	for j in range(0, len(configurations)):
		configuration = configurations[j]

		combinations = configuration['configuration']

		for k in range(0, len(combinations)):
			combination = combinations[k]

			text_for_execution_plan += str(config_number_in_block) + '\t'

			modified_configuration_file = None
			if configuration['is_executable']:
				modified_configuration_file = base_text

			for l in range(0, variables_count):
				variable_value = combination[l]

				if variable_value == '#':
					text_for_execution_plan += 'N/A\t'
				else:
					text_for_execution_plan += variable_value.replace('{', ' ').replace('}', ' ') + '\t'
					if configuration['is_executable']:
						variable_value_without_comments = extra_text_matcher.sub('', variable_value)
						modified_configuration_file = \
							variables_substitution_matchers[l].sub(r"\g<1>" + variable_value_without_comments + r"\g<2>", modified_configuration_file)
			text_for_execution_plan = text_for_execution_plan[:-1] + '\n'

			if configuration['is_executable']:
				with open(result_conf_files_path + 'trackermaster-B' + "%02d" % block_number + '-' + "%03d" % config_number_in_block + '.conf', 'w') as out:
					out.write(modified_configuration_file)

			config_number_in_block += 1
		

with open(result_execution_plan_file, 'w') as out:
	out.write(text_for_execution_plan)
