#!/usr/bin/bash -x

# buildSmall.sh
# Purpose: build small training/validation/test dataset for relevance classifier
# Instructions for use:
#   Create a directory where you want to build the datasets, e.g., data/small
#   cd data/small
#   mkdir LegendsWords                  # if this doesn't exist yet
#   mkdir LegendsWords/Proc1            # if this doesn't exist yet
#   buildSmall.sh                       # <------ i.e., run this script

# get 40 refs for each subset   - this exercises sdBuild1Get.sh
sdBuild1Get.sh --limit 40 --discard

# replace discard_after with 160 refs and keep_after with 80 refs
# This builds a better balanced dataset but is still small
mv discard_after discard_after40
mv keep_after keep_after40
sdGetRawPrimTriage.py -l 160 discard_after > discard_after
sdGetRawPrimTriage.py -l 80 keep_after > keep_after

# Run preprocessing steps
sdBuild2Fig.sh --datadir . --subdir LegendsWords
sdBuild3Pre.sh --datadir LegendsWords --subdir Proc1

# do random split into training, validation, test sets
cd LegendsWords/Proc1
# sdBuild4Split.sh --datadir .                  # to gen a new random split
sdBuild4Split.sh --seed 1609773171 --datadir .
