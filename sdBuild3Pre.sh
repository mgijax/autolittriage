#!/bin/bash
# wrapper to
#  Preprocess extracted figure text files into a Proc* directory

#######################################
# filenames to preprocess
#######################################
files="discard_after keep_after keep_before keep_tumor"

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 --datadir dir --subdir subdir [-- preprocess_options...]

    Apply preprocessing options for sample files:
	$files
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
# preprocess the files
#######################################

for f in $files; do
    set -x
    preprocessSamples.py $* $dataDir/$f  >  $dataDir/$subDir/$f
    set +x
done
