if [ $# -eq 2 ] 
then
    echo "Starting process..."
else
    echo "must be: sh execute_module_and_calculate_metrics.sh ModuleName(e.g.,Background_Subtraction) DoTrackerMasterProcessing(Yes/No)"
    exit
fi

# for example, Background_Subtraction
ModuleName=$1

# Yes or No
MakePythonProcessing=$2

OctavePath="/Applications/Octave.app/Contents/Resources/usr/Cellar/octave/4.0.2_3/bin/octave"


cd ../../trackermaster

if [ "$2" == "Yes" ] ; then
	for f in ../experimental_analysis/configs/$ModuleName/*.conf ; do
		echo $f;
		python __main__.py -i $ModuleName -f $f -m Yes;
		python __main__.py -i $ModuleName -f $f -m No;
	done
fi

cd ../experimental_analysis

# Process positions results

echo name > ./MOT/devkit/seqmaps/$ModuleName.txt

[ -d "./MOT/devkit/res/data/$ModuleName" ] || mkdir ./MOT/devkit/res/data/$ModuleName

# [ -d "$DIRECTORY" ] || mkdir $DIRECTORY

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
[ -d "./processed_results/$ModuleName/counter" ] || mkdir ./processed_results/$ModuleName/counter
[ -d "./processed_results/$ModuleName/times" ] || mkdir ./processed_results/$ModuleName/times

AppendExt="_diff.txt"

cd scripts

# Process counter results

for f in ../raw_results/$ModuleName*-counter.txt ; do
	FileName=$(echo $f | sed 's/^.*\///g' | sed 's/\.txt$//');
	python ./get_counters_metric.py $f $FileName
	mv ../processed_results/$FileName$AppendExt ../processed_results/$ModuleName/counter
done

# Process times results

for f in ../raw_results/$ModuleName*-times.txt ; do
	cp $f ../processed_results/$ModuleName/times/
done


# Process MOT results

cd ../MOT/devkit

[ -d "../../processed_results/$ModuleName/positions" ] || mkdir ../../processed_results/$ModuleName/positions

echo "allMets = evaluateTracking('"$ModuleName".txt', 'res/data/"$ModuleName"/', '../data/');" > ./evalTrackAux.m

$OctavePath --no-gui --no-window-system --silent evalTrackAux.m > ../../processed_results/$ModuleName/positions/MOT_results.txt

rm ./evalTrackAux.m
