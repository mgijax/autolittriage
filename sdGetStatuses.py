#!/usr/bin/env python2.7

#-----------------------------------
'''
  Purpose:
	   run sql to get the curation statuses for documents.

  Outputs:     delimited file to stdout
'''
START_DATE='01/01/2010'	# get statuses for papers created after this date
OutputColumns = [	# this column order is assumed in sampleDataLib.py
    'pubmed',
    'class', 		# "discard" or "keep" (CLASS_NAMES in config file)
    'ap_status',	# A&P curation status (not routed, routed, ...)
    'gxd_status',	# ...
    'go_status',
    'tumor_status',
    'qtl_status',
    'journal',
    ]

#-----------------------------------
import sys
import os
import string
import time
import argparse
import ConfigParser
import db
#-----------------------------------
cp = ConfigParser.ConfigParser()
cp.optionxform = str # make keys case sensitive
cl = ['/'.join(l)+'/config.cfg' for l in [['.']]+[['..']*i for i in range(1,4)]]
configFiles = cp.read(cl)
#print configFiles

# for the output delimited file
FIELDSEP     = '|'		#eval(cp.get("DEFAULT", "FIELDSEP"))
RECORDSEP    = '\n'		#eval(cp.get("DEFAULT", "RECORDSEP"))
CLASS_NAMES  = eval(cp.get("CLASS_NAMES", "y_class_names"))
INDEX_OF_KEEP    = 1		# index in CLASS_NAMES of the keep label
INDEX_OF_DISCARD = 0		# index in CLASS_NAMES of the discard label
#-----------------------------------

def getArgs():
    parser = argparse.ArgumentParser( \
	description='Get papers curation statuses from db, write to stdout')

    parser.add_argument('-s', '--server', dest='server', action='store',
        required=False, default='dev',
        help='db server. Shortcuts:  adhoc, prod, or dev (default)')

    parser.add_argument('-d', '--database', dest='database', action='store',
        required=False, default='mgd',
        help='which database. Example: mgd (default)')

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    args =  parser.parse_args()

    if args.server == 'adhoc':
	args.host = 'mgi-adhoc.jax.org'
	args.db = 'mgd'
    elif args.server == 'prod':
	args.host = 'bhmgidb01.jax.org'
	args.db = 'prod'
    elif args.server == 'dev':
	args.host = 'bhmgidevdb01.jax.org'
	args.db = 'prod'
    else:
	args.host = args.server + '.jax.org'
	args.db = args.database

    return args
#-----------------------------------

SQLSEPARATOR = '||'

# get articles for creation date >= Nov 1, 2017. After lit triage release

# base of query select stmt
BASE_SELECT =  \
'''select a.accid pubmed, r.isdiscard, bs.ap_status,
    bs.gxd_status, 
    bs.go_status, 
    bs.tumor_status, 
    bs.qtl_status,
    r.journal
from bib_refs r join bib_status_view bs on (r._refs_key = bs._refs_key)
     join bib_workflow_data bd on (r._refs_key = bd._refs_key)
     join acc_accession a on
         (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
          and a._mgitype_key=1 )
'''

# list potential queries, best if these are non-overlapping result sets,
#  but only one for now
QUERY_LIST = { \
'query' :  BASE_SELECT +
    '''
    where
    r.creation_date >= '%s'
    and r._createdby_key != 1609      -- littriage_discard user on dev/prod
    and bd.haspdf=1
    -- order by r.journal, pubmed
    ''' % (START_DATE),
}	# end QUERY_LIST
#-----------------------------------

def process():
    """ Main routine"""
    args = getArgs()

    db.set_sqlServer  ( args.host)
    db.set_sqlDatabase( args.db)
    db.set_sqlUser    ("mgd_public")
    db.set_sqlPassword("mgdpub")

    if args.verbose:
	sys.stderr.write( "Hitting database %s %s as mgd_public\n\n" % \
							(args.host, args.db))
    startTime = time.time()

    sys.stdout.write( FIELDSEP.join(OutputColumns) + RECORDSEP )

    for i, q in enumerate(QUERY_LIST.values()):
	qStartTime = time.time()

	results = db.sql( string.split(q, SQLSEPARATOR), 'auto')

	if args.verbose:
	    sys.stderr.write( "Query %d SQL time: %8.3f seconds\n\n" % \
						(i, time.time()-qStartTime))
	nResults = writeResults(results[-1]) # db.sql returns list of rslt lists

	if args.verbose:
	    sys.stderr.write( "%d references processed\n\n" % (nResults) )

    if args.verbose:
	sys.stderr.write( "Total time: %8.3f seconds\n\n" % \
						    (time.time()-startTime))
#-----------------------------------

def writeResults( results	# list of records (dicts)
    ):
    """
    # write records to stdout
    # return count of records written
    """
    for r in results:
	if r['isdiscard'] == 1:
	    sampleClass = CLASS_NAMES[INDEX_OF_DISCARD]
	else:
	    sampleClass = CLASS_NAMES[INDEX_OF_KEEP]
	pmid = str(r['pubmed'])
	ap_status     = str(r['ap_status']).lower()
	gxd_status    = str(r['gxd_status']).lower()
	go_status     = str(r['go_status']).lower()
	tumor_status  = str(r['tumor_status']).lower()
	qtl_status    = str(r['qtl_status']).lower()
	journal       = '_'.join(str(r['journal']).split(' '))

	sys.stdout.write( FIELDSEP.join( [
	    pmid,
	    sampleClass,
	    ap_status,
	    gxd_status,
	    go_status,
	    tumor_status,
	    qtl_status,
	    journal,
	    ] )
	    + RECORDSEP
	    )
    return len(results)
#-----------------------------------

if __name__ == "__main__": process()
