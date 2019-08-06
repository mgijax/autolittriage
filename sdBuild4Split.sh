#!/bin/bash
#    Split raw files into random test, train, validation files
#    Puts all output files into the current directory.

#######################################
# Input file names
#######################################
		# files containing samples after lit triage started,
		# pull random samples from these for test/validation sets
after_nopath="discard_after keep_after" 

		# files containing keeper refs from before lit triage started
		# these are additional keepers to balance the set of discards
		#  from after lit triage started
		# We include ALL of these in the training set.
before_nopath="keep_before keep_tumor"


#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 --rawdir dir

    Split raw files into random test, train, validation files
    Puts all output files into the current directory.

    --rawdir	directory where the raw files live.
    		raw files: ${after_nopath}  ${before_nopath}
ENDTEXT
    exit 5
}
#######################################
# basic setup

projectHome=~/work/autolittriage

splitByJournal=$projectHome/sdSplitByJournal.py
mgiJournals=$projectHome/journalsMonitored.txt	# mgi journals file

splitTestLog=splitTest.log

testFraction="0.15"		# 15% of {keep|discard}_after for test set
valFraction="0.235"		# want 20% {keep|discard}_after
				#  since we are pulling from test leftovers
				#  this is 20%/(1-15%) = .235 of test leftovers

#######################################
# cmdline options
#######################################
rawDir=""

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help)   Usage ;;
    --rawdir)    rawDir="$2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
if [ "$rawDir" == "" ]; then
    Usage
fi
#######################################
# add pathname to raw files
#######################################
after=""
for f in $after_nopath; do
    after="$after $rawDir/$f"
done
before=""
for f in $before_nopath; do
    before="$before $rawDir/$f"
done

#######################################
# from raw files, pull out testSet.txt, valSet.txt, trainSet.txt
#######################################
echo "splitting test validation training sets"
date >$splitTestLog
set -x
# random test set + leftovers
$splitByJournal --alljournals --mgijournals $mgiJournals -f $testFraction --selectedfile testSet.txt  --leftoverfile LeftoversTest.txt $after >>$splitTestLog 2>&1

# random validation set from test set leftovers
$splitByJournal --alljournals --mgijournals $mgiJournals -f $valFraction --selectedfile valSet.txt  --leftoverfile LeftoversVal.txt LeftoversTest.txt >>$splitTestLog 2>&1

# trainSet is valSet leftovers + $before
# (preprocess w/ no preprocessing steps just intelligently concats files)
preprocessSamples.py LeftoversVal.txt $before > trainSet.txt 2>> $splitTestLog
set +x
