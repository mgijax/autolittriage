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
ENDTEXT
    exit 5
}
#######################################
# cmdline options
#######################################
doall=yes
fromdb=no
splittest=no

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help) Usage ;;
    --fromdb) fromdb=yes;doall=no; shift; ;;
    --splittest) splittest=yes;doall=no; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
#echo remaining args: "$*"
echo fromdb "$fromdb"
echo splittest "$splittest"
echo doall "$doall"


projectHome=~/work/autolittriage
mgiJournals=$projectHome/journalsMonitored.txt	# mgi journals filel
tdataGetRaw=$projectHome/tdataGetRaw.py
tdataJournalDist=$projectHome/tdataJournalDist.py
dblog=fromdb.log		# log file from tdataGetRaw
limit="0"			# tdataGetRaw limit (set small for debugging)
				# "0" = no limit

#######################################
# pull raw subsets from db
#######################################
# example if:
if [ "$fromdb" == "yes" -o "$doall" == "yes" ]; then
    echo "getting from db"
    set -x
    $tdataGetRaw -l $limit --server dev --query discard_after > discard_after 2>  $dblog
    $tdataGetRaw -l $limit --server dev --query keep_after    > keep_after    2>> $dblog
    $tdataGetRaw -l $limit --server dev --query keep_before   > keep_before   2>> $dblog
    set +x
fi

#######################################
# from raw files, pull out testSet.txt, valSet.txt
#######################################
if [ "$splittest" == "yes" -o "$doall" == "yes" ]; then
    echo "splitting test validation training sets"
    set -x
    $tdataJournalDist --mgijournals $mgiJournals -f 0.15 --selectedrefs testSet.txt  --leftoverrefs testLeftovers.txt discard_after keep_after &> testSet.log

    # validation fraction: want 20% from all training data
    #  this is 20%/(1-15%) = .235 of testSet leftovers
    $tdataJournalDist --mgijournals $mgiJournals -f 0.235 --selectedrefs valSet.txt  --leftoverrefs valLeftovers.txt testLeftovers.txt &> valSet.log

    # trainingSet is valSet leftovers + keep_before
    # (preprocess w/ no preprocessing steps just intelligently concats files)
    preprocessSamples.py valLeftovers.txt keep_before > trainingSet.txt 2>trainingSet.log
    set +x
fi
