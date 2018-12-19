#!/usr/bin/env python2.7

#-----------------------------------
'''
  Purpose:
	   run sql to get lit triage relevance training set
	   (minor) Data transformations include:
	    replacing non-ascii chars with ' '
	    replacing FIELDSEP and RECORDSEP chars in the doc text w/ ' '

  Outputs:     delimited file to stdout
'''
OutputColumns = [	# this column order is assumed in sampleDataLib.py
    'class', 	# "discard" or "keep" (CLASS_NAMES in config file)
    'pubmed',
    'creation_date',
    'year',
    'journal',
    'title',
    'abstract',
    'text',	# '|\r' replaced by space & convert Unicode to space
    ]

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
CLASS_NAMES  = eval(cp.get("CLASS_NAMES", "y_class_names"))
INDEX_OF_KEEP    = 1		# index in CLASS_NAMES of the keep label
INDEX_OF_DISCARD = 0		# index in CLASS_NAMES of the discard label
#-----------------------------------

def getArgs():
    parser = argparse.ArgumentParser( \
	description='Get littriage relevance training samples, write to stdout')

    parser.add_argument('-s', '--server', dest='server', action='store',
        required=False, default='dev',
        help='db server. Shortcuts:  adhoc, prod, or dev (default)')

    parser.add_argument('-d', '--database', dest='database', action='store',
        required=False, default='mgd',
        help='which database. Example: mgd (default)')

    parser.add_argument('--query', dest='query', action='store',
        required=False, default='all', choices=['all', 
			    'discard_after', 'keep_after', 'keep_before'],
        help='which subset of the training data to get. Default: "all"')

    parser.add_argument('-l', '--limit', dest='nResults',
	required=False, type=int, default=0, 		# 0 means ALL
        help="limit SQL to n results. Default is no limit")

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    args =  parser.parse_args()

    if args.server == 'adhoc':
	args.host = 'mgi-adhoc.jax.org'
	args.db = 'mgd'
    if args.server == 'prod':
	args.host = 'bhmgidb01.jax.org'
	args.db = 'prod'
    if args.server == 'dev':
	args.host = 'bhmgidevdb01.jax.org'
	args.db = 'prod'

    return args
#-----------------------------------

SQLSEPARATOR = '||'

# get articles for creation date >= Nov 1, 2017. After lit triage release

# base of query select stmt
BASE_SELECT =  \
'''
-- skip articles "indexed" by pm2gene and not reviewed by a curator yet
-- we don't really know if these are relevant (not good ground truth)
create temporary table tmp_pm2gene
as
select r._refs_key, a.accid pubmed
from bib_refs r join bib_workflow_status bs
    on (r._refs_key = bs._refs_key and bs.iscurrent=1 )
    join bib_status_view bsv on (r._refs_key = bsv._refs_key)
    join acc_accession a
    on (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
	and a._mgitype_key=1 )
where 
    (bs._status_key = 31576673 and bs._group_key = 31576666 and 
	bs._createdby_key = 1571) -- index for GO by pm2geneload

    and bsv.ap_status in ('Not Routed', 'Rejected')
    and bsv.gxd_status in ('Not Routed', 'Rejected')
    and bsv.tumor_status in ('Not Routed', 'Rejected')
    and bsv.qtl_status in ('Not Routed', 'Rejected')
||
create index idx1 on tmp_pm2gene(_refs_key)
||
select a.accid pubmed, r.isdiscard, r.year,
    to_char(r.creation_date, 'MM/DD/YYYY') as "creation_date",
    r.journal, r.title, r.abstract,
    translate(bd.extractedtext, E'\r', ' ') as "text" -- remove ^M
from bib_refs r join bib_workflow_data bd on (r._refs_key = bd._refs_key)
     join acc_accession a on
         (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
          and a._mgitype_key=1 )
'''

# list potential queries, best if these are non-overlapping result sets result sets result sets result sets
QUERY_LIST = { \
'discard_after' :  BASE_SELECT +
    '''
    where
    r.creation_date > '10/31/2017'
    and not exists (select 1 from tmp_pm2gene t where t._refs_key = r._refs_key)
    and r.isdiscard = 1
    and r._referencetype_key=31576687 -- peer reviewed article
    and r._createdby_key != 1609      -- littriage_discard user on dev/prod
    and bd.haspdf=1
    -- order by r.journal, pubmed
    ''',

'keep_after' :  BASE_SELECT +
    '''
    join bib_status_view bs on (bs._refs_key = r._refs_key)
    where
    r.creation_date > '10/31/2017'
    and not exists (select 1 from tmp_pm2gene t where t._refs_key = r._refs_key)
    and 
    (bs.ap_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.go_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.gxd_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.qtl_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.tumor_status in ('Chosen', 'Indexed', 'Full-coded')
    )
    and r._referencetype_key=31576687 -- peer reviewed article
    and r._createdby_key != 1609      -- littriage_discard user on dev/prod
    and bd.haspdf=1
    -- order by r.journal, pubmed
    ''',

'keep_before' :  BASE_SELECT +
    '''
    join bib_status_view bs on (bs._refs_key = r._refs_key)
    where
    r.creation_date >= '10/1/2016'
    and r.creation_date <= '10/31/2017'
    and not exists (select 1 from tmp_pm2gene t where t._refs_key = r._refs_key)
    and 
    (bs.ap_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.go_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.gxd_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.qtl_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.tumor_status in ('Chosen', 'Indexed', 'Full-coded')
    )
    and r._referencetype_key=31576687 -- peer reviewed article
    and r._createdby_key != 1609      -- littriage_discard user on dev/prod
    and bd.haspdf=1
    -- order by r.journal, pubmed
    ''',
}	# end QUERY_LIST
#-----------------------------------

def getQueries(args):
    """
    Return list of sql queries to run
    """
    if args.query == 'all':
	queries = QUERY_LIST.values()
    else:
	queries = [ QUERY_LIST[args.query] ]

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
	    sampleClass = CLASS_NAMES[INDEX_OF_DISCARD]
	else:
	    sampleClass = CLASS_NAMES[INDEX_OF_KEEP]
	pmid          = str(r['pubmed'])
	creation_date = str(r['creation_date'])
	year          = str(r['year'])
	journal       = '_'.join(str(r['journal']).split(' '))
	title         = str(r['title'])

	# in case we omit these fields during debugging, check if defined
	if r.has_key('abstract'): abstract = str(r['abstract'])
	else: abstract = ''

	if r.has_key('text'): text = str(r['text'])
	else: text = ''

	title    = removeNonAscii(cleanDelimiters(title))
	abstract = removeNonAscii(cleanDelimiters(abstract))
	text     = removeNonAscii(cleanDelimiters(text))

	sys.stdout.write( FIELDSEP.join( [
	    sampleClass,
	    pmid,
	    creation_date,
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
