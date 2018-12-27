#!/bin/bash
# wrapper to
#  Preprocess extracted figure text files into a Proc* directory

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 --datadir dir --procdir subdir [-- preprocess_options...]

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
processDir=""

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help) Usage ;;
    --datadir) dataDir="$2"; shift; shift; ;;
    --procdir) processDir="$2"; shift; shift; ;;
    --)        shift; break ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
# remaining args, $*, are the preprocess params

if [ "$dataDir" == "" -o "$processDir" == "" ]; then
    Usage
fi

#######################################
# filenames for the extracted figure text input files
#######################################
trainFilename=trainSetFig.txt
testFilename=testSetFig.txt
valFilename=valSetFig.txt

trainInput=$dataDir/$trainFilename
testInput=$dataDir/$testFilename
valInput=$dataDir/$valFilename

trainOutput=$dataDir/$processDir/$trainFilename
testOutput=$dataDir/$processDir/$testFilename
valOutput=$dataDir/$processDir/$valFilename

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
