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

    parser.add_argument('--query', dest='queryKey', action='store',
        required=False, default='all',
	choices=['all', 'discard_after', 'keep_after', 'keep_before',
		    'keep_tumor'],
        help='which subset of the training samples to get. Default: "all"')

    parser.add_argument('--stats', dest='stats', action='store_true',
        required=False,
	help="don't get samples, just get counts/stats of samples in db")

    parser.add_argument('-l', '--limit', dest='nResults',
	required=False, type=int, default=0, 		# 0 means ALL
        help="limit SQL to n results. Default is no limit")

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


####################
# SQL fragments used to build up queries
####################
SQLSEPARATOR = '||'
LIT_TRIAGE_DATE = "10/31/2017"		# when we switched to new lit triage
START_DATE = "10/01/2016" 		# earliest date for refs to get
					#  before lit Triage
TUMOR_START_DATE = "07/01/2013"		# date to get add'l tumor papers from

OMIT_SAMPLES_SQL = \
'''
-- Build tmp table of samples to omit.
-- Currently, only one reason to omit:
-- (1) articles "indexed" by pm2gene and not reviewed by a curator yet
--     we don't really know if these are relevant (not good ground truth)
create temporary table tmp_omit
as
select r._refs_key, a.accid pubmed
from bib_refs r join bib_workflow_status bs
    on (r._refs_key = bs._refs_key and bs.iscurrent=1 )
    join bib_status_view bsv on (r._refs_key = bsv._refs_key)
    join acc_accession a
    on (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
	and a._mgitype_key=1 )
where 
    (
	(bs._status_key = 31576673 and bs._group_key = 31576666 and 
	    bs._createdby_key = 1571) -- index for GO by pm2geneload

	and bsv.ap_status in ('Not Routed', 'Rejected')
	and bsv.gxd_status in ('Not Routed', 'Rejected')
	and bsv.tumor_status in ('Not Routed', 'Rejected')
	and bsv.qtl_status in ('Not Routed', 'Rejected')
	and r.creation_date >= '%s'
    )
''' % (START_DATE)   + SQLSEPARATOR + \
'''
create index idx1 on tmp_omit(_refs_key)
'''

# SQL for sample fields to select
BASE_SELECT_FIELDS =  \
'''
select a.accid pubmed, r.isdiscard, r.year,
    to_char(r.creation_date, 'MM/DD/YYYY') as "creation_date",
    r.journal, r.title, r.abstract,
    translate(bd.extractedtext, E'\r', ' ') as "text" -- remove ^M
'''

# SQL for Joins & common where clause components
BASE_SELECT =  \
'''
from bib_refs r join bib_workflow_data bd on (r._refs_key = bd._refs_key)
     join acc_accession a on
         (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
          and a._mgitype_key=1 )
    join bib_status_view bs on (bs._refs_key = r._refs_key)
where
    r._createdby_key != 1609          -- not littriage_discard user
    and r._referencetype_key=31576687 -- peer reviewed article
    and bd.haspdf=1
    and not exists (select 1 from tmp_omit t where t._refs_key = r._refs_key)
    and r.isreviewarticle != 1
'''

# Dict of where clause components for specific queries,
#  these should be non-overlapping result sets
QUERIES = { \
'discard_after' :  BASE_SELECT +
    '''
    and r.isdiscard = 1
    and r.creation_date > '%s' -- After lit triage release
    ''' % LIT_TRIAGE_DATE,
'keep_after' :  BASE_SELECT +
    '''
    and 
    (bs.ap_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.go_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.gxd_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.qtl_status in ('Chosen', 'Indexed', 'Full-coded')
     or bs.tumor_status in ('Chosen', 'Indexed', 'Full-coded')
    )
    and r.creation_date > '%s' -- After lit triage release
    ''' % LIT_TRIAGE_DATE,
'keep_before' :  BASE_SELECT +
    '''
    and 
    (
	(bs.ap_status in ('Chosen', 'Indexed', 'Full-coded')
	 or bs.go_status in ('Chosen', 'Indexed', 'Full-coded')
	 or bs.gxd_status in ('Chosen', 'Indexed', 'Full-coded')
	 or bs.qtl_status in ('Chosen', 'Indexed', 'Full-coded')
	 or bs.tumor_status in ('Chosen', 'Indexed', 'Full-coded')
	)
	and r.creation_date >= '%s' -- after start date
	and r.creation_date <= '%s' -- before lit triage release
    )
    ''' % (START_DATE, LIT_TRIAGE_DATE, ),
'keep_tumor' :  BASE_SELECT +
    '''
    and 
     bs.tumor_status in ('Chosen', 'Indexed', 'Full-coded')
     and r.creation_date >= '%s' -- after tumor start date
     and r.creation_date <= '%s' -- before start date
    ''' % ( TUMOR_START_DATE, START_DATE, ),
}	# end QUERIES
#-----------------------------------

def buildGetSamplesSQL(args):
    """
    Assemble SQL statements (strings) to run to get samples from db.
    Return list of SQL statements.
    """
    # list of keys in QUERIES to run
    if args.queryKey == 'all':
	queryKeys = QUERIES.keys()
    else:
	queryKeys = [ args.queryKey ]

    # Assemble queries
    finalQueries = []
    for i, qk in enumerate(queryKeys):
	if i == 0:		# first select
	    fullSQL = OMIT_SAMPLES_SQL + SQLSEPARATOR
	else: fullSQL = ''

	fullSQL += BASE_SELECT_FIELDS + QUERIES[qk]

	if args.nResults > 0: fullSQL += "\nlimit %d\n" % args.nResults

	finalQueries.append(fullSQL)

    return finalQueries
#-----------------------------------

def process():
    """ Main routine"""
    args = getArgs()

    if False:	# debug SQL
	for i, sql in enumerate(buildGetSamplesSQL(args)):
	    print "%d:" % i
	    print sql
	exit(1)

    db.set_sqlServer  ( args.host)
    db.set_sqlDatabase( args.db)
    db.set_sqlUser    ("mgd_public")
    db.set_sqlPassword("mgdpub")

    if args.verbose:
	sys.stderr.write( "Hitting database %s %s as mgd_public\n\n" % \
							(args.host, args.db))
    startTime = time.time()

    if args.stats: getStats(args)
    else: getSamples(args)

    if args.verbose:
	sys.stderr.write( "Total time: %8.3f seconds\n\n" % \
						    (time.time()-startTime))
#-----------------------------------

def getStats(args):
    '''
    Get counts of sample records from db and write them to stdout
    '''
    selectCount = 'select count(*) as num\n'

    sys.stdout.write(time.ctime() + '\n')

    # Count of records in the omit temp table
    # Do this 1st so tmp table exists for the other queries
    q = OMIT_SAMPLES_SQL + SQLSEPARATOR + selectCount + 'from tmp_omit'
    writeStat("Omitted references (only pm2gene indexed)", q)

    writeStat("Discard after %s" % LIT_TRIAGE_DATE,
					selectCount + QUERIES['discard_after'])
    writeStat("Keep after %s" % LIT_TRIAGE_DATE,
					selectCount + QUERIES['keep_after'])

    writeStat("Keep %s through %s" % (START_DATE, LIT_TRIAGE_DATE),
					selectCount + QUERIES['keep_before'])

    writeStat("Tumor papers %s through %s" % (TUMOR_START_DATE, START_DATE),
					selectCount + QUERIES['keep_tumor'])
#-----------------------------------
def writeStat(label, q):
    results = db.sql( string.split(q, SQLSEPARATOR), 'auto')
    num = results[-1][0]['num']
    sys.stdout.write( "%7d\t%s\n" % (num, label))
#-----------------------------------

def getSamples(args):
    '''
    Run SQL to get samples from DB and output them to stdout
    '''
    # output header line
    sys.stdout.write( FIELDSEP.join(OutputColumns) + RECORDSEP )

    for i, q in enumerate(buildGetSamplesSQL(args)):
	qStartTime = time.time()

	results = db.sql( string.split(q, SQLSEPARATOR), 'auto')

	if args.verbose:
	    sys.stderr.write( "Query %d SQL time: %8.3f seconds\n\n" % \
						(i, time.time()-qStartTime))
	nResults = writeSamples(results[-1]) # db.sql returns list of rslt lists

	if args.verbose:
	    sys.stderr.write( "%d references retrieved\n\n" % (nResults) )
    return

#-----------------------------------

def writeSamples( results	# list of records (dicts)
    ):
    """
    Write records to stdout
    Return count of records written
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
