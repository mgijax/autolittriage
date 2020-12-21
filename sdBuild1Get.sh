#!/bin/bash
# get raw data files

#######################################
# filenames for raw data pulled from db
#######################################
primTriageRawFiles="discard_after keep_after keep_before keep_tumor"
curGroupRawFiles="unselected_after selected_after selected_before"
groups="ap gxd go tumor"

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 {--group groupname |--discard} [--server name] [--limit n] [--norestrict]

    Get raw sample files from the db.
    Puts all files into the current directory.

    --group groupname
		Get data for specific curation group: $groups
    		output files: $curGroupRawFiles

    --discard	Get data for primary triage (discard/keep)
    		output files: $primTriageRawFiles

    --server	Database server: dev (default) or test or prod
    --limit	limit on sql query results (default = 0 = no limit)
    --norestrict when populating raw files, include all articles,
		default: skip review and non-peer reviewed
ENDTEXT
    exit 5
}
#######################################
# basic setup

projectHome=~/work/autolittriage


getRawLog=getRaw.log		# log file from sdGetRaw

#######################################
# cmdline options
#######################################
restrictOpt=''			# default: skip review papers and non-peer rev
limit="0"			# getRaw record limit, "0" = no limit
				#(set small for debugging)
server="dev"
doGroup="unspecified"

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help)   Usage ;;
    --group)     doGroup=yes;group="$2"; shift; shift; ;;
    --discard)   doGroup=no; shift; ;;
    --norestrict) restrictOpt=--norestrict; shift; ;;
    --limit)     limit="$2"; shift; shift; ;;
    --server)    server="$2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
if [ "$doGroup" == "unspecified" ]; then
    Usage
fi
#######################################
# Pull raw subsets from db
#######################################
echo "getting raw data from db: ${server}" | tee -a $getRawLog
date >> $getRawLog
rm -f counts
if [ "$doGroup" == "yes" ]; then
    getRaw=$projectHome/sdGetRawCurGroups.py
    $getRaw --server $server $restrictOpt --group $group --counts | tee -a $getRawLog counts
    for f in $curGroupRawFiles; do
	set -x
	$getRaw --server $server -l $limit $restrictOpt  --group $group --query $f > $f 2>> $getRawLog
	set +x
    done
else
    getRaw=$projectHome/sdGetRawPrimTriage.py
    $getRaw --server $server $restrictOpt --counts | tee -a $getRawLog counts
    for f in $primTriageRawFiles; do
	set -x
	$getRaw --server $server -l $limit $restrictOpt --query $f > $f 2>> $getRawLog
	set +x
    done
fi
