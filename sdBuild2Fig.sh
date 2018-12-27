#!/bin/bash
# wrapper to
#  Apply preprocessing step to extract figure text from training/val/test sets
#  (and save these files)

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 --datadir dir 

    Apply -p figureText option for training/text/val files.
    Files to preprocess are in dir
ENDTEXT
    exit 5
}
#######################################
# cmdline options
#######################################

dataDir=""

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help) Usage ;;
    --datadir) dataDir="$2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done

if [ "$dataDir" == "" ]; then
    Usage
fi

#######################################
# filenames for the extracted figure text input files
#######################################
trainInput=$dataDir/trainSet.txt
testInput=$dataDir/testSet.txt
valInput=$dataDir/valSet.txt

trainOutput=$dataDir/trainSetFig.txt
testOutput=$dataDir/testSetFig.txt
valOutput=$dataDir/valSetFig.txt

figTextOpt="-p figureText"

set -x
preprocessSamples.py $figTextOpt $testInput  >  $testOutput
preprocessSamples.py $figTextOpt $trainInput  >  $trainOutput
set +x
if [ -f $valInput ]; then	# could be no validation file...
    set -x
    preprocessSamples.py $figTextOpt $valInput > $valOutput
    set +x
else
    echo no validation set: $valInput
fi
