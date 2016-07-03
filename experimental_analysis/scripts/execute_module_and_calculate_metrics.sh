#!/bin/sh

if [ $# -eq 3 ] 
then
    echo "Starting process..."
else
    echo "must be: sh path_to_scripts/execute_module_and_calculate_metrics.sh ModuleName(e.g.,Background_Subtraction) DoTrackerMasterProcessing(Yes/No) DoMatlabThings(Yes/No)"
    exit
fi

# for example, Background_Subtraction
ModuleName=$1

# Yes or No
MakePythonProcessing=$2

# Yes or No
MakeMatlabProcessing=$3

MatlabPath="/Applications/MATLAB_R2016a.app/bin/matlab"
OctavePath="/Applications/Octave.app/Contents/Resources/usr/Cellar/octave/4.0.2_3/bin/octave"
Python3Path="python"


cd ../../trackermaster

if [ "$2" = "Yes" ] ; then
	for f in ../experimental_analysis/configs/$ModuleName/*.conf ; do
		echo $f;
		$Python3Path __main__.py -i $ModuleName -f $f -m Yes;
		if [ $? -eq 0 ]; then
			$Python3Path __main__.py -i $ModuleName -f $f -m No;
		else
			exit
		fi
	done
fi

cd ../experimental_analysis

# Process positions results

echo name > ./MOT/devkit/seqmaps/$ModuleName.txt

[ -d "./MOT/devkit/res/data/$ModuleName" ] || mkdir ./MOT/devkit/res/data/$ModuleName

for f in ./raw_results/$ModuleName*-positions.txt ; do
	FileName=$(echo $f | sed 's/^.*\///g' | sed 's/\.txt$//');
	[ -d "./MOT/data/$FileName" ] || mkdir ./MOT/data/$FileName
	[ -d "./MOT/data/$FileName/gt" ] || mkdir ./MOT/data/$FileName/gt
	[ -d "./MOT/data/$FileName/img1" ] || mkdir ./MOT/data/$FileName/img1
	cp ./ground_truth/gt.txt ./MOT/data/$FileName/gt/
	cp $f ./MOT/devkit/res/data/$ModuleName/
	echo $FileName >> ./MOT/devkit/seqmaps/$ModuleName.txt
done

[ -d "./processed_results/$ModuleName" ] || mkdir ./processed_results/$ModuleName

cd scripts

# Process counter results

DirectoryForCounterResults="../processed_results/$ModuleName/counter/"

[ -d "$DirectoryForCounterResults" ] || mkdir $DirectoryForCounterResults
[ -d "$DirectoryForCounterResults/differences" ] || mkdir $DirectoryForCounterResults/differences
[ -d "$DirectoryForCounterResults/differences/data" ] || mkdir $DirectoryForCounterResults/differences/data
[ -d "$DirectoryForCounterResults/histograms" ] || mkdir $DirectoryForCounterResults/histograms
[ -d "$DirectoryForCounterResults/histograms/data" ] || mkdir $DirectoryForCounterResults/histograms/data

for f in ../raw_results/$ModuleName*-counter.txt ; do
	FileName=$(echo $f | sed 's/^.*\///g' | sed 's/\.txt$//');
	$Python3Path ./get_counters_metric.py $f $FileName $DirectoryForCounterResults
done

$Python3Path ./get_counters_latex_histograms.py $DirectoryForCounterResults

# Process times results

[ -d "../processed_results/$ModuleName/times" ] || mkdir ../processed_results/$ModuleName/times
[ -d "../processed_results/$ModuleName/times/data" ] || mkdir ../processed_results/$ModuleName/times/data

for f in ../raw_results/$ModuleName*-times.txt ; do
	cp $f ../processed_results/$ModuleName/times/data/
done

$Python3Path ./get_times_latex_tables.py ../processed_results/$ModuleName/times/


# Process MOT results

if [ "$3" = "Yes" ] ; then
	cd ../MOT/devkit

	[ -d "../../processed_results/$ModuleName/positions" ] || mkdir ../../processed_results/$ModuleName/positions
	[ -d "../../processed_results/$ModuleName/positions/data" ] || mkdir ../../processed_results/$ModuleName/positions/data

	echo "allMets = evaluateTracking('"$ModuleName".txt', 'res/data/"$ModuleName"/', '../data/'); exit();" > ./evalTrackAux.m

	if [ "$MatlabPath" = "" ] ; then
		$OctavePath --no-gui --no-window-system --silent evalTrackAux.m > ../../processed_results/$ModuleName/positions/data/MOT_results.txt
	else
		$MatlabPath -nodesktop -nosplash -r evalTrackAux -logfile ../../processed_results/$ModuleName/positions/data/MOT_results.txt -nojvm -noFigureWindows -nodisplay > /dev/null
	fi

	rm ./evalTrackAux.m

	cd ../../scripts

	$Python3Path mot_results_parser.py ../processed_results/$ModuleName/positions/
fi
