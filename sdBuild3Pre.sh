#!/bin/bash

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 {--discard|--group} --datadir dir --subdir subdir [-- preprocess_options...]

    Apply preprocessing steps to sample files:
    --group     input files are from curation group
    --discard   input files are for discard/keep (primary triage). Default.

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
curationGroup="n"	# default is not by curation group, discard/keep instead

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help) Usage ;;
    --datadir) dataDir="$2"; shift; shift; ;;
    --subdir)  subDir="$2"; shift; shift; ;;
    --group)   curationGroup="y"; shift; ;;
    --discard) curationGroup="n"; shift; ;;
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
if [ "$curationGroup" == "y" ]; then
    files="unselected_after selected_after selected_before"
else
    files="discard_after keep_after keep_before keep_tumor"
fi
#######################################
# preprocess the files
#######################################

echo Running in parallel
date
for f in $files; do
    set -x
    preprocessSamples.py $* $dataDir/$f  >  $dataDir/$subDir/$f 2> $dataDir/$subDir/$f.log &
    set +x
done
wait
echo All Done
date
