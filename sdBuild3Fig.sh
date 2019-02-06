#!/bin/bash
# wrapper to
#  Apply preprocessing step to extract figure text from training/val/test sets
#  (and save these files)

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 --datadir dir --subdir subdir

    Apply -p figureText option for training/text/val files.
    Files to preprocess are in dir
    Processed output files go into subdir
ENDTEXT
    exit 5
}
#######################################
# cmdline options
#######################################

dataDir=""
subDir=""

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help) Usage ;;
    --datadir) dataDir="$2"; shift; shift; ;;
    --subdir)  subDir="$2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done

if [ "$dataDir" == "" -o "$subDir" == "" ]; then
    Usage
fi

#######################################
# filenames for the extracted figure text input files
#######################################
trainInput=$dataDir/trainSet.txt
testInput=$dataDir/testSet.txt
valInput=$dataDir/valSet.txt

trainOutput=$dataDir/$subDir/trainSet.txt
testOutput=$dataDir/$subDir/testSet.txt
valOutput=$dataDir/$subDir/valSet.txt

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
