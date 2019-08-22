#!/bin/bash
#    Split raw files into random test, train, validation files
#    Puts all output files into the current directory.


#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 {--group|--discard} --datadir dir

    Split sample files into random test, train, validation files

    --group     sample files are from curation group
    --discard   sample files are for discard/keep (primary triage). Default.

    --datadir	directory where the input files live.
    Puts all output files into the current directory.
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
dataDir=""
curationGroup="n"       # default is not by curation group, discard/keep instead

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help)   Usage ;;
    --datadir) dataDir="$2"; shift; shift; ;;
    --group)   curationGroup="y"; shift; ;;
    --discard) curationGroup="n"; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
if [ "$dataDir" == "" ]; then
    Usage
fi
#######################################
# Input file names
# "after" are files containing samples after lit triage started,
#	pull random samples from these for test/validation sets
# "before" are files containing "yes" refs from before lit triage started
#	these are additional keepers to balance the set of "no"s from "after".
#	We include ALL of these in the training set.
#######################################
if [ "$curationGroup" == "n" ]; then
    after_nopath="discard_after keep_after" 
    before_nopath="keep_before keep_tumor"
else
    after_nopath="unselected_after selected_after" 
    before_nopath="selected_before"
fi
#######################################
# add pathname to filenames
#######################################
after=""
for f in $after_nopath; do
    after="$after $dataDir/$f"
done
before=""
for f in $before_nopath; do
    before="$before $dataDir/$f"
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
