# for example, Background_Subtraction
SectionName=$1

# Yes or No
MakePythonProcessing=$2

cd ../../trackermaster

if [ "$2" == "Yes" ] ; then
	for f in ../experimental_analysis/configs/$SectionName/*.conf ; do
		echo $f;
		python __main__.py -i $SectionName -f $f -m Yes;
		python __main__.py -i $SectionName -f $f -m No;
	done
fi

cd ../experimental_analysis

# Process positions results

echo name > ./MOT/devkit/seqmaps/$SectionName.txt
mkdir ./MOT/devkit/res/data/$SectionName

for f in ./raw_results/$SectionName*-positions.txt ; do
	FileName=$(echo $f | sed 's/^.*\///g' | sed 's/\.txt$//');
	mkdir ./MOT/data/$FileName
	mkdir ./MOT/data/$FileName/gt
	mkdir ./MOT/data/$FileName/img1
	cp ./ground_truth/gt.txt ./MOT/data/$FileName/gt/
	cp $f ./MOT/devkit/res/data/$SectionName/
	echo $FileName >> ./MOT/devkit/seqmaps/$SectionName.txt
done

mkdir ./processed_results/$SectionName
mkdir ./processed_results/$SectionName/counter
mkdir ./processed_results/$SectionName/times
AppendExt="_diff.txt"

cd scripts

# Process counter results

for f in ../raw_results/$SectionName*-counter.txt ; do
	FileName=$(echo $f | sed 's/^.*\///g' | sed 's/\.txt$//');
	python ./get_counters_metric.py $f $FileName
	mv ../processed_results/$FileName$AppendExt ../processed_results/$SectionName/counter
done

# Process times results

for f in ../raw_results/$SectionName*-times.txt ; do
	cp $f ../processed_results/$SectionName/times/
done
