#!/usr/bin/env python2.7

#-----------------------------------
'''
  Purpose:
	   run sql to get set of papers added to backpopulate 'discard' papers.
	   (minor) Data transformations include:
	    replacing non-ascii chars with ' '
	    replacing FIELDSEP and RECORDSEP chars in the doc text w/ ' '

  Outputs:      Delimited file to stdout
		See sampleDataLib.ClassifiedSample for output format
'''
#-----------------------------------
import sys
import os
import string
import re
import time
import argparse
import db
import sampleDataLib
#-----------------------------------

sampleObjType = sampleDataLib.PrimTriageClassifiedSample

# for the Sample output file
outputSampleSet = sampleDataLib.ClassifiedSampleSet(sampleObjType=sampleObjType)
RECORDEND    = outputSampleSet.getRecordEnd()
FIELDSEP     = sampleObjType.getFieldSep()

#-----------------------------------

def getArgs():
    parser = argparse.ArgumentParser( \
	description='Get backpopulated articles, write to stdout')

    parser.add_argument('--test', dest='test', action='store_true',
        required=False,
	help="just run ad hoc test code")

    parser.add_argument('-s', '--server', dest='server', action='store',
        required=False, default='dev',
        help='db server. Shortcuts:  adhoc, prod, or dev (default)')

    parser.add_argument('-d', '--database', dest='database', action='store',
        required=False, default='mgd',
        help='which database. Example: mgd (default)')

    parser.add_argument('--query', dest='queryKey', action='store',
        required=False, default='backpopulated',
	choices=['backpopulated'],
        help='which subset of the training samples to get. Default: "backpopulated"')

    parser.add_argument('--counts', dest='counts', action='store_true',
        required=False,
	help="don't get samples, just get counts")

    parser.add_argument('-l', '--limit', dest='nResults',
	required=False, type=int, default=0, 		# 0 means ALL
        help="limit SQL to n results. Default is no limit")

    parser.add_argument('--textlength', dest='maxTextLength',
	type=int, required=False, default=None,
	help="only include the 1st n chars of text fields (for debugging)")

    parser.add_argument('--norestrict', dest='restrictArticles',
	action='store_false', required=False,
	help="include all articles, default: skip review and non-peer reviewed")

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

args = getArgs()

####################
# SQL fragments used to build up queries
####################
SQLSEPARATOR = '||'
LIT_TRIAGE_DATE = "10/31/2017"		# when we switched to new lit triage
START_DATE = "10/01/2016" 		# earliest date for refs to get
					#  before lit Triage
TUMOR_START_DATE = "07/01/2013"		# date to get add'l tumor papers from

#----------------
# SQL to build tmp tables 
#----------------
BUILD_TMP_TABLES = [ \
    # Tmp table of samples to omit.
    # Currently, only one reason to omit:
    # (1) articles "indexed" by pm2gene and not reviewed by a curator yet
    #     we don't really know if these are relevant (not good ground truth)
'''
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
''' % (START_DATE),
'''
    create index tmp_idx1 on tmp_omit(_refs_key)
''',
    # tmp table of references matching initial criteria. Need this tmp tble
    #  to make subsequent selects run fast.
'''
    create temporary table tmp_refs
    as
    select distinct r._refs_key, r.creation_date
    from bib_refs r join bib_workflow_data bd on (r._refs_key = bd._refs_key)
    where r._createdby_key = 1609          -- ONLY littriage_discard user
       and bd.extractedtext is not null
       and not exists (select 1 from tmp_omit t where t._refs_key = r._refs_key)
''',
'''
    create index tmp_idx2 on tmp_refs(_refs_key)
''',
    # this index is important for speed since bib_refs does not have an index on
    #  creation_date
'''
    create index tmp_idx3 on tmp_refs(creation_date)
''',
]
#----------------
# We get the data for a reference in 2 steps (separate SQL):
#  (1) basic ref info
#  (2) extracted text parts (body, references, star methods, ...)
# Then we concat the text parts in the right order to get the full ext text
#  and then join this to the basic ref info.
#----------------
# SQL Parts for getting basic info on refs (not extracted text)
#----------------
BASE_FIELDS =  \
'''
select distinct r._refs_key,
    r.isdiscard, r.year,
    to_char(r.creation_date, 'MM/DD/YYYY') as "creation_date",
    r.isreviewarticle,
    typeTerm.term as ref_type,
    'ignore supp term' as supp_status,
    -- suppTerm.term as supp_status,
    r.journal, r.title, r.abstract,
    a.accid pubmed,
    bsv.ap_status,
    bsv.gxd_status, 
    bsv.go_status, 
    bsv.tumor_status, 
    bsv.qtl_status
'''
BASE_FROM =  \
'''
from bib_refs r join tmp_refs tr on (r._refs_key = tr._refs_key)
    join bib_workflow_data bd on (r._refs_key = bd._refs_key)
    join bib_status_view bsv on (r._refs_key = bsv._refs_key)
    -- join voc_term suppTerm on (bd._supplemental_key = suppTerm._term_key)
    join voc_term typeTerm on (r._referencetype_key = typeTerm._term_key)
    join acc_accession a on
         (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
          and a._mgitype_key=1 and a.preferred=1 )
'''
RESTRICT_REF_TYPE = \
'''
    and r._referencetype_key=31576687 -- peer reviewed article
    and r.isreviewarticle != 1
'''
#----------------
# SQL Parts for getting extracted text parts so they can be catted together
#----------------
EXTTEXT_FIELDS =  \
'''
select bd._refs_key, bd.extractedtext as text_part, t.term as text_type
'''
EXTTEXT_FROM =  \
'''
from bib_refs r join tmp_refs tr on (r._refs_key = tr._refs_key)
    join bib_workflow_data bd on (r._refs_key = bd._refs_key)
    join voc_term t on (bd._extractedtext_key = t._term_key)
    join bib_status_view bsv on (r._refs_key = bsv._refs_key)
'''
#----------------
# SQL Parts for getting counts of references
#----------------
COUNTS_FIELDS = 'select count(distinct r._refs_key) as num\n'
COUNTS_FROM =  \
'''
from bib_refs r join tmp_refs tr on (r._refs_key = tr._refs_key)
    join bib_status_view bsv on (r._refs_key = bsv._refs_key)
    join acc_accession a on
         (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
          and a._mgitype_key=1 and a.preferred=1)
'''
#----------------
# SQL where clauses for each subset of refs to get
#----------------
# Dict of where clause components for specific queries,
#  these should be non-overlapping result sets
# These where clauses are shared between the basic ref SQL, extracted
#  text SQL, and counts SQL

WHERE_CLAUSES = { \
'backpopulated' :
    '''
    -- backpopulated
    ''',
'discard_after' :
    '''
    -- discard_after
    where r.isdiscard = 1
    and tr.creation_date > '%s' -- After lit triage release
    ''' % LIT_TRIAGE_DATE,
'keep_after' :
    '''
    -- keep_after
    where 
    (bsv.ap_status in ('Chosen', 'Indexed', 'Full-coded')
     or bsv.go_status in ('Chosen', 'Indexed', 'Full-coded')
     or bsv.gxd_status in ('Chosen', 'Indexed', 'Full-coded')
     or bsv.qtl_status in ('Chosen', 'Indexed', 'Full-coded')
     or bsv.tumor_status in ('Chosen', 'Indexed', 'Full-coded')
    )
    and tr.creation_date > '%s' -- After lit triage release
    ''' % LIT_TRIAGE_DATE,
'keep_before' :
    '''
    -- keep_before
    where 
    (bsv.ap_status in ('Chosen', 'Indexed', 'Full-coded')
     or bsv.go_status in ('Chosen', 'Indexed', 'Full-coded')
     or bsv.gxd_status in ('Chosen', 'Indexed', 'Full-coded')
     or bsv.qtl_status in ('Chosen', 'Indexed', 'Full-coded')
     or bsv.tumor_status in ('Chosen', 'Indexed', 'Full-coded')
    )
    and tr.creation_date >= '%s' -- after start date
    and tr.creation_date <= '%s' -- before lit triage release
    ''' % (START_DATE, LIT_TRIAGE_DATE, ),
'keep_tumor' :
    '''
    -- keep_tumor
    where 
     bsv.tumor_status in ('Chosen', 'Indexed', 'Full-coded')
     and tr.creation_date >= '%s' -- after tumor start date
     and tr.creation_date <= '%s' -- before start date
    ''' % ( TUMOR_START_DATE, START_DATE, ),
}	# end WHERE_CLAUSES
#-----------------------------------

class ExtractedTextSet (object):
    """
    IS	a collection of extracted text records (from multiple references)
    Has	each record is dict with fields
	{'_refs_key' : int, 'text_type': (e.g, 'body', 'references'), 
	 'text_part': text} 
	The records may have other fields too that are not used here.
	The field names '_refs_key', 'text_type', 'text_part' are specifiable.
    DOES (1)collects and concatenates all the fields for a given _refs_key into
	a single text field in the correct order - thus recapitulating the 
	full extracted text.
	(2) join a set of basic reference records to their extracted text
    """
    # from Vocab_key = 142 (Lit Triage Extracted Text Section vocab)
    validTextTypes = [ 'body', 'reference',
			'author manuscript fig legends',
			'star methods',
			'supplemental', ]
    #-----------------------------------

    def __init__(self,
	extTextRcds,		# list of rcds as above
	keyLabel='_refs_key',	# name of the reference key field
	typeLabel='text_type',	# name of the text type field
	textLabel='text_part',	# name of the text field
	):
	self.keyLabel  = keyLabel
	self.typeLabel = typeLabel
	self.textLabel = textLabel
	self.extTextRcds = extTextRcds
	self.key2TextParts = self.gatherExtText()
    #-----------------------------------

    def gatherExtText(self, ):
	"""
	Gather the extracted text sections for each _refs_key
	Return dict { _refs_key: { extratedTextType : text } }
	E.g., { 12345 : {   'body'        : 'body section text',
			    'references'  : 'ref section text',
			    'star methods': '...text...',
			    } }
	"""
	resultDict = {}
	for r in self.extTextRcds:
	    refKey   = r[self.keyLabel]
	    textType = r[self.typeLabel]
	    textPart = r[self.textLabel]

	    if textType not in self.validTextTypes:
		raise ValueError("Invalid extracted text type: '%s'\n" % \
								    textType)
	    if not resultDict.has_key(refKey):
		resultDict[refKey] = {}

	    resultDict[refKey][textType] = textPart
	return resultDict
    #-----------------------------------

    def joinRefs2ExtText(self,
			refRcds,
			refKeyLabel='_refs_key',
			extTextLabel='ext_text',
			allowNoText=True,
	):
	"""
	Assume refRcds is a list of records { refKeyLabel : xxx, ...}
	For each record in the list, add a field: extTextLabel: text 
	"""
	for r in refRcds:
	    refKey = r[refKeyLabel]

	    if not allowNoText and not self.key2TextParts.has_key(refKey):
		raise ValueError("No extracted text found for '%s'\n" % \
								    str(refKey))

	    r[extTextLabel] = self.getExtText(refKey)

	return refRcds
    #-----------------------------------

    def getExtText(self, refKey ):

	extTextDict = self.key2TextParts.get(refKey,{})

	text =  extTextDict.get('body','') + \
		extTextDict.get('reference', '') + \
		extTextDict.get('author manuscript fig legends', '') + \
		extTextDict.get('star methods', '') + \
		extTextDict.get('supplemental', '')
	return text
    #-----------------------------------
# end class ExtractedTextSet -----------------------------------

####################
def main():
####################
    db.set_sqlServer  ( args.host)
    db.set_sqlDatabase( args.db)
    db.set_sqlUser    ("mgd_public")
    db.set_sqlPassword("mgdpub")

    verbose( "Hitting database %s %s as mgd_public\n" % (args.host, args.db))
    verbose( "Query option:  %s\n" % args.queryKey)

    startTime = time.time()

    if args.counts: doCounts(args)
    else: doSamples(args)

    verbose( "Total time: %8.3f seconds\n\n" % (time.time()-startTime))
#-----------------------------------

def buildGetSamplesSQL(args, ):
    """
    Assemble SQL statements (strings) to run to get samples from db.
    Return list of pairs of SQL (basic fields query, text query)
    """
    # list of keys in WHERE_CLAUSES to run
    if args.queryKey == 'all':
	queryKeys = WHERE_CLAUSES.keys()
    else:
	queryKeys = [ args.queryKey ]

    # Assemble shared query parts
    baseSQL = BASE_FIELDS + BASE_FROM
    textSQL = EXTTEXT_FIELDS + EXTTEXT_FROM

    if args.restrictArticles:
	restrict = RESTRICT_REF_TYPE
	verbose("Omitting review and non-peer reviewed articles\n")
    else:
	restrict = ''
	verbose("Including review and non-peer reviewed articles\n")

    if args.nResults > 0: limitSQL = "\nlimit %d\n" % args.nResults
    else: limitSQL = ''

    # Add in specific where clauses
    queryPairs = []

    for qk in queryKeys:
	fullBaseSQL = baseSQL + WHERE_CLAUSES[qk] + restrict + limitSQL
	fullTextSQL = textSQL + WHERE_CLAUSES[qk] + restrict + limitSQL
	queryPairs.append( (fullBaseSQL, fullTextSQL) )

    return queryPairs
#-----------------------------------

def doSamples(args):
    '''
    Run SQL to get samples from DB and output them to stdout
    '''
    global outputSampleSet
    db.sql( BUILD_TMP_TABLES, 'auto')

    for i, (baseQ, textQ) in enumerate(buildGetSamplesSQL(args)):
	refRecords = getQueryResults(i, baseQ, textQ)

	for r in refRecords:
	    sample = sqlRecord2ClassifiedSample( r)
	    outputSampleSet.addSample( sample)

    startTime = time.time()
    verbose("writing %d samples:\n" % outputSampleSet.getNumSamples())

    nResults = writeSamples(outputSampleSet)
    verbose( "%8.3f seconds\n\n" %  (time.time()-startTime))
    return
#-----------------------------------

def getQueryResults(i, baseQ, textQ):
    """
    Run SQL for basic fields and extracted text fields, & join them.
    Return list of records.
    Each record represents one article w/ its basic fields & its extracted text
    """
    #### get basic reference fields
    startTime = time.time()
    refResults = db.sql( string.split(baseQ, SQLSEPARATOR), 'auto')
    refRcds = refResults[-1]

    verbose( "Query %d:  %d references retrieved\n" % (i, len(refRcds)))
    verbose( "SQL time: %8.3f seconds\n\n" % (time.time()-startTime))

    #### get extended text parts
    startTime = time.time()
    extTextResults = db.sql(string.split(textQ, SQLSEPARATOR), 'auto')
    extTextRcds = extTextResults[-1]

    verbose( "Query %d:  %d extracted text rcds retrieved\n" % \
						(i, len(extTextRcds)))
    verbose( "SQL time: %8.3f seconds\n\n" % (time.time()-startTime))

    #### join basic fields and extracted text
    startTime = time.time()
    verbose( "Joining ref info to extracted text:\n")

    extTextSet = ExtractedTextSet( extTextRcds )
    extTextSet.joinRefs2ExtText( refRcds, allowNoText=True )

    verbose( "%8.3f seconds\n\n" %  (time.time()-startTime))

    return refRcds
#-----------------------------------

def writeSamples(sampleSet):
    sampleSet.setMetaItem('host', args.host)
    sampleSet.setMetaItem('db', args.db)
    sampleSet.setMetaItem('time', time.strftime("%Y/%m/%d-%H:%M:%S"))
    sampleSet.write(sys.stdout)
#-----------------------------------

def sqlRecord2ClassifiedSample( r,		# sql Result record
    ):
    """
    Encapsulates knowledge of ClassifiedSample.setFields() field names
    """
    newR = {}
    newSample = sampleObjType()

    if r['isdiscard'] == 1:
	knownClassIndex = newSample.getY_negative()
    else:
	knownClassIndex = newSample.getY_positive()

    newR['knownClassName']= newSample.getClassNames()[ knownClassIndex ]
   
    newR['ID']            = str(r['pubmed'])
    newR['creationDate']  = str(r['creation_date'])
    newR['year']          = str(r['year'])
    newR['journal']       = '_'.join(str(r['journal']).split(' '))
    newR['title']         = cleanUpTextField(r, 'title')
    newR['abstract']      = cleanUpTextField(r, 'abstract')
    newR['extractedText'] = cleanUpTextField(r, 'ext_text')
    if args.maxTextLength: newR['extractedText'] += '\n'
    newR['isReview']      = str(r['isreviewarticle'])
    newR['refType']       = str(r['ref_type'])
    newR['suppStatus']    = str(r['supp_status'])
    newR['apStatus']      = str(r['ap_status'])
    newR['gxdStatus']     = str(r['gxd_status'])
    newR['goStatus']      = str(r['go_status'])
    newR['tumorStatus']   = str(r['tumor_status']) 
    newR['qtlStatus']     = str(r['qtl_status'])

    return newSample.setFields(newR)
#-----------------------------------

def cleanUpTextField(rcd,
		    textFieldName,
    ):
    # in case we omit this text field during debugging, check if defined
    if rcd.has_key(textFieldName): text = str(rcd[textFieldName])
    else: text = ''

    if args.maxTextLength:	# handy for debugging
	text = text[:args.maxTextLength]
	text = text.replace('\n', ' ')

    text = removeNonAscii( cleanDelimiters( text))
    return text
#-----------------------------------

def doCounts(args):
    '''
    Get counts of sample records from db and write them to stdout
    '''
    sys.stdout.write(time.ctime() + '\n')

    # Count of records in the omit temp table
    # Do this 1st so tmp table exists for the other queries
    selectCount = 'select count(distinct _refs_key) as num from tmp_omit\n'
    q = BUILD_TMP_TABLES + [selectCount]
    
    writeStat("Omitted references (only pm2gene indexed)", SQLSEPARATOR.join(q))

    baseSQL = COUNTS_FIELDS + COUNTS_FROM
    if args.restrictArticles:
	restrict = RESTRICT_REF_TYPE
	sys.stdout.write("Omitting review and non-peer reviewed articles\n")
    else:
	restrict = ''
	sys.stdout.write("Including review and non-peer reviewed articles\n")

    writeStat("Discard after %s" % LIT_TRIAGE_DATE,
			baseSQL + WHERE_CLAUSES['discard_after'] + restrict)

    writeStat("Keep after %s" % LIT_TRIAGE_DATE,
			baseSQL + WHERE_CLAUSES['keep_after'] + restrict)

    writeStat("Keep before %s through %s" % (START_DATE, LIT_TRIAGE_DATE),
			baseSQL + WHERE_CLAUSES['keep_before'] + restrict)

    writeStat("Tumor papers %s through %s" % (TUMOR_START_DATE, START_DATE),
			baseSQL + WHERE_CLAUSES['keep_tumor'] + restrict)
#-----------------------------------

def writeStat(label, q):
    results = db.sql( string.split(q, SQLSEPARATOR), 'auto')
    num = results[-1][0]['num']
    sys.stdout.write( "%7d\t%s\n" % (num, label))
#-----------------------------------

def cleanDelimiters(text):
    """ remove RECORDEND and FIELDSEPs from text (replace w/ ' ')
    """
    new = text.replace(RECORDEND,' ').replace(FIELDSEP,' ')
    return new
#-----------------------------------

nonAsciiRE = re.compile(r'[^\x00-\x7f]')	# match non-ascii chars
def removeNonAscii(text):
    return nonAsciiRE.sub(' ',text)
#-----------------------------------

def verbose(text):
    if args.verbose:
	sys.stderr.write(text)
	sys.stderr.flush()
#-----------------------------------

if __name__ == "__main__":
    if not (len(sys.argv) > 1 and sys.argv[1] == '--test'):
	main()
    else: 			# ad hoc test code
	if True:	# debug SQL
	    for i, (b,t) in enumerate(buildGetSamplesSQL(args, )):
		print "%d:" % i
		print b
		print t
	if True:	# test ExtractedTextSet
	    authFig = 'author manuscript fig legends'
	    rcds = [ \
		{'rk':'1234', 'ty': 'body', 'text_part': 'here is a body text'},
		{'rk':'1234', 'ty': 'reference','text_part':' & ref text'},
		{'rk':'1234', 'ty': 'supplemental', 'text_part':' & supp text'},
		{'rk':'1234', 'ty': 'star methods', 'text_part':' & star text'},
		{'rk':'1234', 'ty': authFig, 'text_part': ' & author figs'},
		{'rk':'2345', 'ty': 'body', 'text_part': 'a second body text'},
		{'rk':'4567', 'ty': 'supplemental', 'text_part': 'text'},
		]
	    refs = [ \
		    {'_refs_key' : '1234', 'otherfield':'xyz',}, 
		    {'_refs_key' : '2345', 'otherfield':'stu',}, 
		    {'_refs_key' : '7890', 'otherfield':'stu',}, # no rcd above
		]
	    ets = ExtractedTextSet( rcds, keyLabel='rk', typeLabel='ty',)
	    print ets.gatherExtText()
	    print "%s: '%s'" % ('1234', ets.getExtText('1234'))
	    print "%s: '%s'" % ('2345', ets.getExtText('2345'))
	    print "%s: '%s'" % ('7890', ets.getExtText('7890'))
	    refs = ets.joinRefs2ExtText(refs, allowNoText=True)
	    print refs
	    try:
		refs = ets.joinRefs2ExtText(refs, allowNoText=False)
	    except ValueError:
		(t,val,traceback) = sys.exc_info()
		print 'Correctly got %s exception:\n%s' % (str(t),val)
