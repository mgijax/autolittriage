#!/bin/bash
# get raw data files and do random training/validation/test set splits

#######################################
# filenames for raw data pulled from db
#######################################
discardAfter=discard_after	# discard refs from Nov 2017 to present
keepAfter=keep_after		# keeper refs from Nov 2017 to present
keepBefore=keep_before		# keeper refs from before Nov 2017
				#   (used to balance discard vs. keep)
statusFile=refStatuses.txt	# reference curation statuses
revStatusFile=reviewStatus.txt	# reference review statuses

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 [--getraw] [--findrevs] [--rmrevs] [--splittest] [--doall]

    Build training, validation, and test datasets - starting from db
    Also get references curation status file.
    Puts all files into the current directory.

    --getraw	Only pull raw files from db.
    		raw files: ${discardAfter}, ${keepAfter}, ${keepBefore}....
		status file: ${statusFile}
		Pulls from dev db.
    --findrevs	Run analysis to find review papers from pubmed & text analysis
    --rmrevs	Remove review papers from raw files
    --splittest	Only split out test, validation, and training sets
    --doall	Do all the above (default)

    --limit	limit on sql query results (default = no limit)
ENDTEXT
    exit 5
}
#######################################
# basic setup

projectHome=~/work/autolittriage

getRaw=$projectHome/sdGetRaw.py
findReviews=$projectHome/sdFindReviews.py
removeReviews=$projectHome/sdRemoveReviews.py
splitByJournal=$projectHome/sdSplitByJournal.py
getStatuses=$projectHome/sdGetStatuses.py

mgiJournals=$projectHome/journalsMonitored.txt	# mgi journals file

getRawLog=getRaw.log		# log file from sdGetRaw
reviewsLog=reviews.log
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
doFindRevs=no
doRmRevs=no
doSplittest=no
limit="0"			# getRaw record limit, "0" = no limit
				#(set small for debugging)
while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help)   Usage ;;
    --doall)     doAll=yes; shift; ;;
    --getraw)    doGetRaw=yes;doAll=no; shift; ;;
    --findrevs)  doFindRevs=yes;doAll=no; shift; ;;
    --rmrevs)    doRmRevs=yes;doAll=no; shift; ;;
    --splittest) doSplittest=yes;doAll=no; shift; ;;
    --limit)     limit="$2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
#######################################
# pull raw subsets from db
#######################################
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
# run analysis to create file specifying which articles are review refs
#######################################
if [ "$doFindRevs" == "yes" -o "$doAll" == "yes" ]; then
    echo "creating file containing article review statuses"
    date >>$reviewsLog
    set -x
    cat $discardAfter $keepAfter $keepBefore | $findReviews >$revStatusFile 2>> $reviewsLog
    set +x
fi
#######################################
# remove review articles from raw files
#######################################
if [ "$doRmRevs" == "yes" -o "$doAll" == "yes" ]; then
    echo "removing review articles from the raw sample files"
    date >>$reviewsLog
    for f in $discardAfter $keepAfter $keepBefore; do
	newName=${f}_withReviews
	set -x
	mv $f $newName
	$removeReviews -r $revStatusFile $newName > $f 2>> $reviewsLog
	set +x
    done
fi
#######################################
# from raw files, pull out testSet.txt, valSet.txt, trainSet.txt
#######################################
if [ "$doSplittest" == "yes" -o "$doAll" == "yes" ]; then
    echo "splitting test validation training sets"
    date >$splitTestLog
    set -x
    # random test set + leftovers
    $splitByJournal --mgijournals $mgiJournals -f $testFraction --selectedrefs testSet.txt  --leftoverrefs testLeftovers.txt $discardAfter $keepAfter >>$splitTestLog 2>&1

    # random validation set from test set leftovers
    $splitByJournal --mgijournals $mgiJournals -f $valFraction --selectedrefs valSet.txt  --leftoverrefs valLeftovers.txt testLeftovers.txt >>$splitTestLog 2>&1

    # trainSet is valSet leftovers + $keepBefore
    # (preprocess w/ no preprocessing steps just intelligently concats files)
    preprocessSamples.py valLeftovers.txt $keepBefore > trainSet.txt 2>> $splitTestLog
    set +x
fi
