#!/bin/bash
# example bash script

function Usage() {
    cat - <<ENDTEXT

$0 [--fromdb] [--splittest]

    Build training, validation, and test datasets - starting w/ db
    Puts all files into the current directory.

    --fromdb	pull raw files from db
    --splittest	split out test, validation, and training sets
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
tdataGetRaw=$projectHome/tdataGetRaw.py
tdataJournalDist=$projectHome/tdataJournalDist.py
getRawLog=getRaw.log		# log file from tdataGetRaw
splitTestLog=splitTest.log

#######################################
# cmdline options
#######################################
doAll=yes
doGetRaw=no
doSplittest=no
limit="0"			# tdataGetRaw limit (set small for debugging)
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
    $tdataGetRaw -l $limit --server dev --query discard_after > discard_after 2>  $getRawLog
    $tdataGetRaw -l $limit --server dev --query keep_after    > keep_after    2>> $getRawLog
    $tdataGetRaw -l $limit --server dev --query keep_before   > keep_before   2>> $getRawLog
    set +x
fi
#######################################
# from raw files, pull out testSet.txt, valSet.txt, trainingSet.txt
#######################################
if [ "$doSplittest" == "yes" -o "$doAll" == "yes" ]; then
    echo "splitting test validation training sets"
    set -x
    $tdataJournalDist --mgijournals $mgiJournals -f 0.15 --selectedrefs testSet.txt  --leftoverrefs testLeftovers.txt discard_after keep_after &> $splitTestLog

    # validation fraction: want 20% from all training data
    #  this is 20%/(1-15%) = .235 of testSet leftovers
    $tdataJournalDist --mgijournals $mgiJournals -f 0.235 --selectedrefs valSet.txt  --leftoverrefs valLeftovers.txt testLeftovers.txt >>$splitTestLog 2>&1

    # trainingSet is valSet leftovers + keep_before
    # (preprocess w/ no preprocessing steps just intelligently concats files)
    preprocessSamples.py valLeftovers.txt keep_before > trainingSet.txt 2>> $splitTestLog
    set +x
fi
