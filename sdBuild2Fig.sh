#!/bin/bash
# wrapper to
#  Apply preprocessing step to extract figure text from raw sample files
#  (and save these files)

#######################################
# filenames for the extracted figure text input files
#######################################
files="discard_after keep_after keep_before keep_tumor"

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 --datadir dir --subdir subdir

    Apply -p figureText option for discard and keep raw sample files.
	files: $files
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
# extract figure text
#######################################
figTextOpt="-p figureText"

for f in $files; do
    set -x
    preprocessSamples.py $figTextOpt $dataDir/$f  >  $dataDir/$subDir/$f
    set +x
done
