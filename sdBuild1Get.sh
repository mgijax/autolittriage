#!/bin/bash
# get raw data files and do random training/validation/test set splits

#######################################
# filenames for raw data pulled from db
#######################################
discardAfter=discard_after	# discard refs from Nov 2017 to present
keepAfter=keep_after		# keeper refs from Nov 2017 to present
keepBefore=keep_before		# keeper refs from before Nov 2017
				#   (used to balance discard vs. keep)
statusFile=refStatuses.txt

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 [--fromdb] [--splittest]

    Build training, validation, and test datasets - starting from db
    Also get references curation status file.
    Puts all files into the current directory.

    --fromdb	only pull raw files from db.
    		raw files: ${discardAfter}, ${keepAfter}, ${keepBefore}....
		status file: ${statusFile}
		Pulls from dev db.
    --splittest	only split out test, validation, and training sets
	    (default is do all the above)

    --limit	limit on sql query results (default = no limit)
ENDTEXT
    exit 5
}
#######################################
# basic setup
#######################################
projectHome=~/work/autolittriage
mgiJournals=$projectHome/journalsMonitored.txt	# mgi journals filel
getRaw=$projectHome/sdGetRaw.py
splitByJournal=$projectHome/sdSplitByJournal.py
getStatuses=$projectHome/sdGetStatuses.py
getRawLog=getRaw.log		# log file from sdGetRaw
splitTestLog=splitTest.log
testFraction="0.15"		# 15% of {keep|discard}_after for test set
valFraction="0.235"		# want 20% {keep|discard}_after
				#  since we are pulling from test leftovers
				#  this is 20%/(1-15%) = .235 of test leftovers

#######################################
# cmdline options
#######################################
doAll=yes
doGetRaw=no
doSplittest=no
limit="0"			# getRaw limit (set small for debugging)
				# "0" = no limit
while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help) Usage ;;
    --fromdb) doGetRaw=yes;doAll=no; shift; ;;
    --splittest) doSplittest=yes;doAll=no; shift; ;;
    --limit) limit="$2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
#######################################
# pull raw subsets from db
#######################################
# example if:
if [ "$doGetRaw" == "yes" -o "$doAll" == "yes" ]; then
    echo "getting raw data from db"
    set -x
    $getRaw --stats >$getRawLog
    $getRaw -l $limit --server dev --query $discardAfter > $discardAfter 2>> $getRawLog
    $getRaw -l $limit --server dev --query $keepAfter    > $keepAfter    2>> $getRawLog
    $getRaw -l $limit --server dev --query $keepBefore   > $keepBefore   2>> $getRawLog
    $getStatuses > $statusFile  2>> $getRawLog
    set +x
fi
#######################################
# from raw files, pull out testSet.txt, valSet.txt, trainSet.txt
#######################################
if [ "$doSplittest" == "yes" -o "$doAll" == "yes" ]; then
    echo "splitting test validation training sets"
    set -x
    # random test set + leftovers
    $splitByJournal --mgijournals $mgiJournals -f $testFraction --selectedrefs testSet.txt  --leftoverrefs testLeftovers.txt $discardAfter $keepAfter &> $splitTestLog

    # random validation set from test set leftovers
    $splitByJournal --mgijournals $mgiJournals -f $valFraction --selectedrefs valSet.txt  --leftoverrefs valLeftovers.txt testLeftovers.txt >>$splitTestLog 2>&1

    # trainSet is valSet leftovers + $keepBefore
    # (preprocess w/ no preprocessing steps just intelligently concats files)
    preprocessSamples.py valLeftovers.txt $keepBefore > trainSet.txt 2>> $splitTestLog
    set +x
fi
