# for example, Background_Subtraction
SectionName=$1

cd ../../trackermaster

#for f in ../experimental_analisis/configs/$SectionName/*.conf ;
#do
#	echo $f;
#	python __main__.py -i $SectionName -f $f -m Yes;
#	python __main__.py -i $SectionName -f $f -m No;
#done

cd ../experimental_analysis

echo name > ./MOT/devkit/seqmaps/$SectionName.txt
mkdir ./MOT/devkit/res/data/$SectionName

for f in ./raw_results/$SectionName*-positions.txt ;
do
	FileName=$(echo $f | sed 's/^.*\///g' | sed 's/\.txt$//');
	mkdir ./MOT/data/$FileName
	mkdir ./MOT/data/$FileName/gt
	mkdir ./MOT/data/$FileName/img1
	cp ./MOT/original_gt/gt.txt ./MOT/data/$FileName/gt/
	cp $f ./MOT/devkit/res/data/$SectionName/
	echo $FileName >> ./MOT/devkit/seqmaps/$SectionName.txt
done
