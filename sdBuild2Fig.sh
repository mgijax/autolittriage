#!/bin/bash
# wrapper to
#  Apply preprocessing step to extract figure text from raw sample files
#  (and save these files)


#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 {--discard|--group} --datadir dir --subdir subdir

    Apply -p figureText extraction to sample files.
    --group	sample files are from curation group
    --discard	sample files are for discard/keep (primary triage). Default.

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
curationGroup="n"	# default is not by curation group, discard/keep instead

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help) Usage ;;
    --datadir) dataDir="$2"; shift; shift; ;;
    --subdir)  subDir="$2"; shift; shift; ;;
    --group)   curationGroup="y"; shift; ;;
    --discard) curationGroup="n"; shift; ;;
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
if [ "$curationGroup" == "y" ]; then
    files="selected_after selected_before unselected_after"
else
    files="discard_after keep_after keep_before keep_tumor"
fi
#######################################
# extract figure text
#######################################
figTextOpt="-p figureTextLegCloseWords50"

for f in $files; do
    set -x
    preprocessSamples.py $figTextOpt $dataDir/$f  >  $dataDir/$subDir/$f
    set +x
done
