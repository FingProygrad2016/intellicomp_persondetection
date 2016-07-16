#!/bin/bash

if [ $# -eq 7 ] 
then
    echo "Starting process..."
else
	echo ""
    echo "must be: sh path_to_scripts/execute_module_and_calculate_metrics.sh ModuleName DoTrackerMasterProcessing DoOnlyBlockNumber MinConfigNumber MaxConfigNumber ProcessResults DoMatlabThings"
    echo ""
    echo "ModuleName (e.g.,Background_Subtraction)"
    echo "DoTrackerMasterProcessing ('Yes'/'No')"
    echo "DoOnlyBlockNumber (0 for all)"
    echo "MinConfigNumber (0 for no limit; DoOnlyBlockNumber must be non 0)"
    echo "MaxConfigNumber (0 for no limit; DoOnlyBlockNumber must be non 0)"
    echo "ProcessResults ('Yes'/'No'; it is automatically 'No' if DoOnlyBlockNumber is not 0)"
    echo "DoMatlabThings ('Yes'/'No')"
    exit
fi

# for example, Background_Subtraction
ModuleName=$1

# Yes or No
MakePythonProcessing=$2

# Block number (0 for all)
Block=$3
# Min config number (Block number must be different from 0; 0 for no limit)
MinConfig=$4
# Max config number (Block number must be different from 0; 0 for no limit)
MaxConfig=$5

if [ "$Block" -eq 0 ] ; then
	# Yes or No (it is "No" if Block number is not 0)
	ProcessResults=$6
else
	ProcessResults="No"
fi

# Yes or No
MakeMatlabProcessing=$7

MatlabPath="" # /Applications/MATLAB_R2016a.app/bin/matlab"
OctavePath="/Applications/Octave.app/Contents/Resources/usr/Cellar/octave/4.0.2_3/bin/octave"
Python3Path="python"
MaxThreads=4
MaxConfigsPerSequence=10


module_block_config_matcher=".*-B([0-9]+)-([0-9]+)"

cd ../../trackermaster

if [ "$MakePythonProcessing" = "Yes" ] ; then
	for f in ../experimental_analysis/configs/$ModuleName/*.conf ; do
		
		[[ $f =~ $module_block_config_matcher ]]
		
		BlockNumber=${BASH_REMATCH[1]}
		ConfigNumber=${BASH_REMATCH[2]}

		if [ "$Block" -eq 0 ] ; then
			echo $f;
			$Python3Path __main__.py -i $ModuleName -f $f -m Yes;
			if [ $? -eq 0 ]; then
				$Python3Path __main__.py -i $ModuleName -f $f -m No;
			else
				exit
			fi
		else
			if [ "$Block" -eq "$BlockNumber" ] ; then
				if [ "$MinConfig" -eq 0 ] ; then
					if [ "$MaxConfig" -eq 0 ]; then
						echo $f;
						$Python3Path __main__.py -i $ModuleName -f $f -m Yes;
						if [ $? -eq 0 ]; then
							$Python3Path __main__.py -i $ModuleName -f $f -m No;
						else
							exit
						fi
					else
						if [ "$MaxConfig" -ge "$ConfigNumber" ] ; then
							echo $f;
							$Python3Path __main__.py -i $ModuleName -f $f -m Yes;
							if [ $? -eq 0 ]; then
								$Python3Path __main__.py -i $ModuleName -f $f -m No;
							else
								exit
							fi
						fi
					fi
				else
					if [ "$MinConfig" -le "$ConfigNumber" ] ; then
						if [ "$MaxConfig" -eq 0 ]; then
							echo $f;
							$Python3Path __main__.py -i $ModuleName -f $f -m Yes;
							if [ $? -eq 0 ]; then
								$Python3Path __main__.py -i $ModuleName -f $f -m No;
							else
								exit
							fi
						else
							if [ "$MaxConfig" -ge "$ConfigNumber" ] ; then
								echo $f;
								$Python3Path __main__.py -i $ModuleName -f $f -m Yes;
								if [ $? -eq 0 ]; then
									$Python3Path __main__.py -i $ModuleName -f $f -m No;
								else
									exit
								fi
							fi
						fi
					fi
				fi
			fi
		fi
	done
fi

if [ "$ProcessResults" = "Yes" ] ; then

	cd ../experimental_analysis

	# Process positions results

	[ -d "./MOT/devkit/res/data/$ModuleName" ] || mkdir ./MOT/devkit/res/data/$ModuleName

	configs_count=1
	seqmap_count=1

	echo name > ./MOT/devkit/seqmaps/${ModuleName}_$(printf %03d ${seqmap_count}).txt

	for f in ./raw_results/$ModuleName*-positions.txt ; do
		FileName=$(echo $f | sed 's/^.*\///g' | sed 's/\.txt$//');
		[ -d "./MOT/data/$FileName" ] || mkdir ./MOT/data/$FileName
		[ -d "./MOT/data/$FileName/gt" ] || mkdir ./MOT/data/$FileName/gt
		[ -d "./MOT/data/$FileName/img1" ] || mkdir ./MOT/data/$FileName/img1
		cp ./ground_truth/gt.txt ./MOT/data/$FileName/gt/
		cp $f ./MOT/devkit/res/data/$ModuleName/

		echo $FileName >> ./MOT/devkit/seqmaps/${ModuleName}_$(printf %03d ${seqmap_count}).txt

		if [ "$configs_count" -eq $MaxConfigsPerSequence ]; then
			(( configs_count = 1 ))
			(( seqmap_count += 1 ))
			echo name > ./MOT/devkit/seqmaps/${ModuleName}_$(printf %03d ${seqmap_count}).txt
		else
			(( configs_count += 1 ))
		fi
	done

	[ -d "./processed_results/$ModuleName" ] || mkdir ./processed_results/$ModuleName

	cd scripts

	# Process counter results

	DirectoryForCounterResults="../processed_results/$ModuleName/counter/"

	[ -d "$DirectoryForCounterResults" ] || mkdir $DirectoryForCounterResults
	[ -d "$DirectoryForCounterResults/differences" ] || mkdir $DirectoryForCounterResults/differences
	[ -d "$DirectoryForCounterResults/differences/data" ] || mkdir $DirectoryForCounterResults/differences/data
	[ -d "$DirectoryForCounterResults/differences/out" ] || mkdir $DirectoryForCounterResults/differences/out
	[ -d "$DirectoryForCounterResults/histograms" ] || mkdir $DirectoryForCounterResults/histograms
	[ -d "$DirectoryForCounterResults/histograms/data" ] || mkdir $DirectoryForCounterResults/histograms/data
	[ -d "$DirectoryForCounterResults/histograms/out" ] || mkdir $DirectoryForCounterResults/histograms/out

	for f in ../raw_results/$ModuleName*-counter.txt ; do
		FileName=$(echo $f | sed 's/^.*\///g' | sed 's/\.txt$//');
		$Python3Path ./get_counters_metric.py $f $FileName $DirectoryForCounterResults
	done

	$Python3Path ./get_counters_latex_tables.py $DirectoryForCounterResults
	$Python3Path ./get_counters_latex_histograms.py $DirectoryForCounterResults

	# Process times results

	[ -d "../processed_results/$ModuleName/times" ] || mkdir ../processed_results/$ModuleName/times
	[ -d "../processed_results/$ModuleName/times/data" ] || mkdir ../processed_results/$ModuleName/times/data
	[ -d "../processed_results/$ModuleName/times/out" ] || mkdir ../processed_results/$ModuleName/times/out

	for f in ../raw_results/$ModuleName*-times.txt ; do
		cp $f ../processed_results/$ModuleName/times/data/
	done

	$Python3Path ./get_times_latex_tables.py ../processed_results/$ModuleName/times/


	# Process MOT results

	cd ../MOT/devkit

	[ -d "../../processed_results/$ModuleName/positions" ] || mkdir ../../processed_results/$ModuleName/positions
	[ -d "../../processed_results/$ModuleName/positions/data" ] || mkdir ../../processed_results/$ModuleName/positions/data
	[ -d "../../processed_results/$ModuleName/positions/out" ] || mkdir ../../processed_results/$ModuleName/positions/out

	if [ "$MakeMatlabProcessing" = "Yes" ] ; then

		count=1
		p_count=1
		pids=""

		for f in ./seqmaps/$ModuleName_*.txt ; do
			FileName=$(echo $f | sed 's/^.*\///g');
			echo "allMets = evaluateTracking('"$FileName"', 'res/data/"$ModuleName"/', '../data/'); exit();" > ./evalTrackAux_$(printf %03d $count).m

			if [ "$MatlabPath" = "" ] ; then
				$OctavePath --no-gui --no-window-system --silent evalTrackAux_$(printf %03d $count).m > ../../processed_results/$ModuleName/positions/data/MOT_results_$(printf %03d $count).txt &
			else
				$MatlabPath -nodesktop -nosplash -r evalTrackAux_$(printf %03d $count) -logfile ../../processed_results/$ModuleName/positions/data/MOT_results_$(printf %03d $count).txt -nojvm -noFigureWindows -nodisplay > /dev/null &
			fi

			pids+="$! "

			if [ "$p_count" -eq $MaxThreads ]; then
				for pid in $pids; do
				    wait $pid
				    if [ $? -eq 0 ]; then
				        echo "SUCCESS - Job $pid exited with a status of $?"
				    else
				        echo "FAILED - Job $pid exited with a status of $?"
				    fi
				done
				(( p_count = 1 ))
				pids=""
			else
				(( p_count += 1 ))
			fi

			(( count += 1 ))

		done

		for pid in $pids; do
		    wait $pid
		    if [ $? -eq 0 ]; then
		        echo "SUCCESS - Job $pid exited with a status of $?"
		    else
		        echo "FAILED - Job $pid exited with a status of $?"
		    fi
		done
		
		rm ./evalTrackAux_*.m

	fi

	cd ../../scripts

	$Python3Path mot_results_parser.py ../processed_results/$ModuleName/positions/
fi

exit
