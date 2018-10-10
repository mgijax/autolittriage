#!/usr/bin/env python2.7 
#
"""
    getTrainingData.py

    Pull articles from the database, get their
	pmid,
	title, abstract,
	extracted text,
	journal, 
	MGI-discard y/n
    Populate text files with title+abstract+extracted text concat'd together.
    
    Output naming
	/no	# MGI-discards (not relevant) go here
	/yes	# non-discards (relevant) go here
	   /journalname		# under /no and /yes, journal directories
	       /pmid.txt	# the smooshed together text file

    also output to stdout a summary report, tab delimited:
    pmid,
    yes/no,
    journal,

# Author: Jim Kadin
##
"""
import sys
#sys.path.append('..')
#sys.path.append('../..')
import string
import time
import os
import argparse
import db
#import sampleDataLib as sdlib
#from ConfigParser import ConfigParser
#import sampleDataLib as sdLib
#import sklearnHelperLib as ppLib	# module holding preprocessor function

#-----------------------------------
DEFAULT_OUTPUT_DIR = '.'
TEXT_PART_SEP         = '::::\n'	# separates title, abstract, ext text

def getArgs():
    parser = argparse.ArgumentParser( \
    description='get articles from db, write them to directory structure')

#    parser.add_argument('inputFile', action='store', 
#    	help='tab-delimited input file of training data')

    parser.add_argument('-o', '--outputDir', dest='outputDir', action='store',
	required=False, default=DEFAULT_OUTPUT_DIR,
    	help='dir where /no and /yes go. Default=%s' % DEFAULT_OUTPUT_DIR)

#    parser.add_argument('-p', '--preprocessor', dest='preprocessor',
#	action='store', required=False, default=PREPROCESSOR,
#    	help='preprocessor function name. Default= %s' % PREPROCESSOR)

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    parser.add_argument('-s', '--server', dest='server', action='store',
        required=False, default='dev',
        help='db server: adhoc, prod, or dev (default)')

    args = parser.parse_args()

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
#----------------------
SQLSEPARATOR = '||'
QUERY =  \
'''
select a.accid pubmed, r.isdiscard, r.year, r.journal, r.title, r.abstract, bd.extractedtext
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
order by r.journal, pubmed
limit 10
'''

def main():

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
    baseDir = args.outputDir
    for yesNo in ['yes', 'no']:
	dirname =  os.sep.join( [ baseDir, yesNo ] )
	if not os.path.exists(dirname):
	    os.makedirs(dirname)

    for i,r in enumerate(results[-1]):
	pmid          = r['pubmed']
	yesNo         = 'yes'		# default to yes (relevant)
	if r['isdiscard'] == 1:
	    yesNo     = 'no'		# nope
	year          = str(r['year'])
	journal       = '_'.join(r['journal'].split(' '))
	title         = r['title']

	# in case we omit these fields during debugging, check if defined
	if r.has_key('abstract'): abstract = r['abstract']
	else: abstract = ''
	if r.has_key('extractedtext'): extractedText = r['extractedtext']
	else: extractedText = ''

	# Journal directory
	dirname = os.sep.join( [ baseDir, yesNo, journal ] )
	if not os.path.exists(dirname):
	    os.makedirs(dirname)

	# Text file
	filename = os.sep.join( [ dirname, pmid + ".txt" ] )
	fp = open(filename, 'w')
	text = TEXT_PART_SEP.join([title, abstract, extractedText])
	fp.write(text)
	fp.close()

	# Write to summary report
	sys.stdout.write( \
	    '\t'.join([
		pmid,
		yesNo,
		year,
		journal,
		title[:20],
		#abstract,
		#extractedText,
		]) + '\n')
    return
#-----------------------------------

if __name__ == "__main__":
    main()
