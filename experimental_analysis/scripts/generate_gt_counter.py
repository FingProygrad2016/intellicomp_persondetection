#!/usr/bin/python3

gt_path = "../ground_truth/gt.txt"
frame_count_person = {}

with open(gt_path, 'r') as gt:
  for line in gt:
    dataline = line.split(",")
    frame_count_person[dataline[0]] = frame_count_person.get(dataline[0], 0) + 1

frame_count_person = frame_count_person.items()
frame_count_person = sorted(frame_count_person, key=lambda x: int(x[0]))

with open('../ground_truth/gt_counter.txt', 'w') as out:
  for f in frame_count_person:
    out.write("%s,%s\n" % f)
