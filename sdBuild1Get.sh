#!/bin/bash
# get raw data files

#######################################
# filenames for raw data pulled from db
#######################################
rawFiles="discard_after keep_after keep_before keep_tumor"

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 [--limit n] [--norestrict] [--getraw] [--doall]

    Get raw sample files from the db.
    Puts all files into the current directory.

    --getraw	Only pull raw files from db.
    		raw files: $rawFiles
		Pulls from dev db.
    --doall	Do all the above (default)

    --limit	limit on sql query results (default = no limit)
    --norestrict when populating raw files, include all articles,
		default: skip review and non-peer reviewed
ENDTEXT
    exit 5
}
#######################################
# basic setup

projectHome=~/work/autolittriage

getRaw=$projectHome/sdGetRaw.py

getRawLog=getRaw.log		# log file from sdGetRaw

#######################################
# cmdline options
#######################################
doAll=yes
doGetRaw=no
restrictOpt=''			# default: skip review papers and non-peer rev
limit="0"			# getRaw record limit, "0" = no limit
				#(set small for debugging)
while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help)   Usage ;;
    --doall)     doAll=yes; shift; ;;
    --getraw)    doGetRaw=yes;doAll=no; shift; ;;
    --norestrict) restrictOpt=--norestrict; shift; ;;
    --limit)     limit="$2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
#######################################
# Pull raw subsets from db
#######################################
if [ "$doGetRaw" == "yes" -o "$doAll" == "yes" ]; then
    echo "getting raw data from db"
    set -x
    $getRaw $restrictOpt --stats >$getRawLog
    for f in $rawFiles; do
	$getRaw -l $limit $restrictOpt --server dev --query $f > $f 2>> $getRawLog
    done
    set +x
fi
