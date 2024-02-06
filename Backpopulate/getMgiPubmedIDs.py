#
#  Purpose:
#	   run sql to get references and their extracted text.
#
#  Outputs:     writes directories named by Journal and writes extracted text
#		files (named by Pubmed ID) into those directories
#
###########################################################################
import sys
import os
import string
import time
import argparse
#from ConfigParser import ConfigParser
import db

#-----------------------------------

def getArgs():
    parser = argparse.ArgumentParser( \
                    description='get extracted text for references')

    parser.add_argument('-s', '--server', dest='server', action='store',
        required=False, default='dev',
        help='db server: adhoc, prod, or dev (default)')

    parser.add_argument('-o', '--output', dest='outputFile', action='store',
        required=False, default='pubmedIDs.tsv',
        help="output directory. Default: 'pubmedIDs.tsv'")

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    args =  parser.parse_args()

    if args.server == 'adhoc':
	args.host = 'mgi-adhoc.jax.org'
	args.db = 'mgd'
    if args.server == 'prod':
	args.host = 'bhmgidb01'
	args.db = 'prod'
    if args.server == 'dev':
	args.host = 'bhmgidevdb01'
	args.db = 'prod'

    return args
###################################3

SQLSEPARATOR = '||'
QUERY =  \
'''
select a.accid pubmed, bd.haspdf, r.year, r.journal
from bib_refs r join bib_workflow_data bd on (r._refs_key = bd._refs_key)
     join acc_accession a on
	 (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
	  and a._mgitype_key=1 )
where
r.year >= 2010
-- and r._referencetype_key=31576687 -- peer reviewed article
-- and bd.haspdf=1
-- r.isdiscard = 1
-- and bd._supplemental_key =34026997  -- "supplemental attached"
order by r.journal, pubmed
-- limit 10
'''


def getPubmedIDs():

    args = getArgs()

    db.set_sqlServer  ( args.host)
    db.set_sqlDatabase( args.db)
    db.set_sqlUser    ("mgd_public")
    db.set_sqlPassword("mgdpub")

    if args.verbose:
	sys.stderr.write( "Hitting database %s %s as mgd_public\n\n" % \
							(args.host, args.db))

    queries = string.split(QUERY, SQLSEPARATOR)

    startTime = time.time()
    results = db.sql( queries, 'auto')
    endTime = time.time()
    if args.verbose:
	sys.stderr.write( "Total SQL time: %8.3f seconds\n\n" % \
							(endTime-startTime))

    fp = open(args.outputFile, 'w')
    fp.write( '\t'.join( [
	'pubmed',
	'haspdf',
	'year',
	'journal', ] ) + '\n' )
    for i,r in enumerate(results[-1]):
	fp.write( '\t'.join( [
	    str(r['pubmed']),
	    str(r['haspdf']),
	    str(r['year']),
	    r['journal'], ] ) + '\n' )
	if args.verbose and i % 1000 == 0:	# write progress indicator
	    sys.stderr.write('%d..' % i)

# end getExtractedText() ----------------------------------

#
#  MAIN
#
if __name__ == "__main__": getPubmedIDs()
