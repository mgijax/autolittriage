#!/bin/bash
# take raw data files and do random training/validation/test set splits

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 [--rawdir]

    Split raw files into random test, train, validation files
    Puts all files into the current directory.

    --rawdir	directory where the raw files live.
    		raw files: ${discardAfter}, ${keepAfter}, ${keepBefore}....
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
# from raw files, pull out testSet.txt, valSet.txt, trainSet.txt
#######################################
		# files containing samples after lit triage started,
		# pull random samples from these for test/validation sets
after="$rawDir/discard_after $rawDir/keep_after" 

		# files containing keeper refs from before lit triage started
		# these are additional keepers to balance the set of discards
		#  from after lit triage started
before="$rawDir/keep_before" 
#before="$rawDir/keep_before $rawDir/keep_tumor"  # when we've split out tumor

echo "splitting test validation training sets"
date >$splitTestLog
set -x
# random test set + leftovers
$splitByJournal --mgijournals $mgiJournals -f $testFraction --selectedrefs testSet.txt  --leftoverrefs LeftoversTest.txt $after >>$splitTestLog 2>&1

# random validation set from test set leftovers
$splitByJournal --mgijournals $mgiJournals -f $valFraction --selectedrefs valSet.txt  --leftoverrefs LeftoversVal.txt LeftoversTest.txt >>$splitTestLog 2>&1

# trainSet is valSet leftovers + $before
# (preprocess w/ no preprocessing steps just intelligently concats files)
preprocessSamples.py LeftoversVal.txt $before > trainSet.txt 2>> $splitTestLog
set +x
