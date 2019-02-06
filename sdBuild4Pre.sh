#!/bin/bash
# wrapper to
#  Preprocess extracted figure text files into a Proc* directory

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 --datadir dir --subdir subdir [-- preprocess_options...]

    Apply preprocessing options for training/text/val files.
    Files to preprocess are in dir
    Store resulting files in dir/subdir
    Preprocess options are typically:  -p removeURLsCleanStem
	(steps defined in sampleDataLib.py)
    If no preprocessing options, will just copy the files to dir/subdir
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
    --subdir) subDir="$2"; shift; shift; ;;
    --)        shift; break ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
# remaining args, $*, are the preprocess params

if [ "$dataDir" == "" -o "$subDir" == "" ]; then
    Usage
fi

#######################################
# filenames for the extracted figure text input files
#######################################
trainFilename=trainSet.txt
testFilename=testSet.txt
valFilename=valSet.txt

trainInput=$dataDir/$trainFilename
testInput=$dataDir/$testFilename
valInput=$dataDir/$valFilename

trainOutput=$dataDir/$subDir/$trainFilename
testOutput=$dataDir/$subDir/$testFilename
valOutput=$dataDir/$subDir/$valFilename

set -x
preprocessSamples.py $* $testInput  >  $testOutput
preprocessSamples.py $* $trainInput > $trainOutput
set +x
if [ -f $valInput ]; then	# could be no validation file...
    set -x
    preprocessSamples.py $* $valInput > $valOutput
    set +x
else
    echo no validation set: $valInput
fi
