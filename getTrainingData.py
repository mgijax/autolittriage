#!/usr/bin/env python2.7

#-----------------------------------
'''
  Purpose:
	   run sql to get lit triage relevance training set
	   Data transformations include:
	    replacing non-ascii chars with ' '
	    replacing FIELDSEP and RECORDSEP chars in the doc text w/ ' '

  Outputs:     delimited file to stdout
'''
OutputColumns = [
    'class', 	# "discard" or "keep" (CLASS_NAMES in config file)
    'pubmed',
    'year',
    'journal',
    'title',
    'abstract',
    'text',	# '|\r' replaced by space & convert Unicode to space
    ]	# this column order is assumed in sampleDataLib.py

#-----------------------------------
# Try to keep this script easy to run from various servers,
# Try to keep import dependencies down to standard Python libaries
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
FIELDSEP     = eval(cp.get("DEFAULT", "FIELDSEP"))
RECORDSEP    = eval(cp.get("DEFAULT", "RECORDSEP"))
CLASS_NAMES  = eval(cp.get("DEFAULT", "CLASS_NAMES"))
INDEX_OF_YES = eval(cp.get("DEFAULT", "INDEX_OF_YES"))
INDEX_OF_NO  = eval(cp.get("DEFAULT", "INDEX_OF_NO"))
#-----------------------------------

def getArgs():
    parser = argparse.ArgumentParser( \
	description='Get littriage relevance training samples, write to stdout')

    parser.add_argument('-s', '--server', dest='server', action='store',
        required=False, default='dev',
        help='db server. Shortcuts:  adhoc, prod, or dev (default)')

    parser.add_argument('-d', '--database', dest='database', action='store',
        required=False, default='mgd',
        help='Which database. Example: mgd (default)')

    parser.add_argument('--query', dest='query', action='store',
        required=False, default='all', choices=['all', ],
        help='which subset of the training data to get, for now only "all"')

    parser.add_argument('-l', '--limit', dest='nResults',
	type=int, default=0, 		# 0 means ALL
        help="limit SQL to n results. Default is no limit")

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
#-----------------------------------

SQLSEPARATOR = '||'

# get articles for year > 2017
Query1 =  \
'''
select a.accid pubmed, r.isdiscard, r.year, r.journal, r.title, r.abstract,
     translate(bd.extractedtext, E'\r', ' ') as "text" -- remove ^M
from bib_refs r join bib_workflow_data bd on (r._refs_key = bd._refs_key)
     join acc_accession a on
         (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
          and a._mgitype_key=1 )
where
r.year > 2017
and r._referencetype_key=31576687 -- peer reviewed article
and bd.haspdf=1
-- r.isdiscard = 1
-- and bd._supplemental_key =34026997  -- "supplemental attached"
-- order by r.journal, pubmed
'''
#-----------------------------------

def getQueries(args):
    """
    Return list of sql queries to run
    """
    if args.query == 'someoption':
	queries = ['someQuery']
    else:
	queries = [Query1]

    if args.nResults > 0:
	limitText = "\nlimit %d\n" % args.nResults
	final = []
	for q in queries:
	    final.append( q + limitText )
    else: final = queries

    return final
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

    for i, q in enumerate(getQueries(args)):
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
	    sampleClass = CLASS_NAMES[INDEX_OF_NO]
	else:
	    sampleClass = CLASS_NAMES[INDEX_OF_YES]
	pmid          = str(r['pubmed'])
	year          = str(r['year'])
	journal       = '_'.join(r['journal'].split(' '))
	title         = r['title']

	# in case we omit these fields during debugging, check if defined
	if r.has_key('abstract'): abstract = r['abstract']
	else: abstract = ''

	if r.has_key('text'): text = r['text']
	else: text = ''

	title    = removeNonAscii(cleanDelimiters(title))
	abstract = removeNonAscii(cleanDelimiters(abstract))
	text     = removeNonAscii(cleanDelimiters(text))

	sys.stdout.write( FIELDSEP.join( [
	    sampleClass,
	    pmid,
	    year,
	    journal,
	    title,
	    abstract,
	    text,
	    ] )
	    + RECORDSEP
	)
    return len(results)
#-----------------------------------

def cleanDelimiters(text):
    """ remove RECORDSEPs and FIELDSEPs from text (replace w/ ' ')
    """
    # not the most efficient way to do this ...
    new = text.replace(RECORDSEP,' ').replace(FIELDSEP,' ')
    return new
#-----------------------------------

def removeNonAscii(text):
    new = ''.join([i if ord(i) < 128 else ' ' for i in text])
    return new
#-----------------------------------

if __name__ == "__main__": process()
