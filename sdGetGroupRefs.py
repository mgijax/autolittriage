#!/usr/bin/env python2.7

#-----------------------------------
'''
  Purpose:
	   run sql to get lit triage relevance training set
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
import ConfigParser
import db
import sampleDataLib
#-----------------------------------
cp = ConfigParser.ConfigParser()
cp.optionxform = str # make keys case sensitive
cl = ['/'.join(l)+'/config.cfg' for l in [['.']]+[['..']*i for i in range(1,4)]]
configFiles = cp.read(cl)
#print configFiles

# for the output delimited file
FIELDSEP     = eval(cp.get("DEFAULT", "FIELDSEP"))
RECORDEND    = eval(cp.get("DEFAULT", "RECORDEND"))
CLASS_NAMES  = eval(cp.get("CLASS_NAMES", "y_class_names"))
INDEX_OF_KEEP    = 1		# index in CLASS_NAMES of the keep label
INDEX_OF_DISCARD = 0		# index in CLASS_NAMES of the discard label
#-----------------------------------

def getArgs():
    parser = argparse.ArgumentParser( \
	description='Get littriage relevance training samples, write to stdout')

    parser.add_argument('--test', dest='test', action='store_true',
        required=False,
	help="just run ad hoc test code")

    parser.add_argument('-s', '--server', dest='server', action='store',
        required=False, default='dev',
        help='db server. Shortcuts:  adhoc, prod, or dev (default)')

    parser.add_argument('-d', '--database', dest='database', action='store',
        required=False, default='mgd',
        help='which database. Example: mgd (default)')

    parser.add_argument('--group', dest='group', action='store', required=True, 
	choices=['ap', 'gxd', 'go', 'tumor',], help='which curation group')

    parser.add_argument('--query', dest='queryKey', action='store',
        required=False, default='all',
        help='which subset of the reference samples to get')

    parser.add_argument('--counts', dest='counts', action='store_true',
        required=False, help="don't get references, just get counts")

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

db.set_sqlServer  ( args.host)
db.set_sqlDatabase( args.db)
db.set_sqlUser    ("mgd_public")
db.set_sqlPassword("mgdpub")

#-----------------------------------

class BaseRefSearch (object): # {
    """
    Is:   base class for a reference (article) search from the database
    Has:  all the necessary SQL for the search, the result set, 
    Does: Encapsulates the common SQL for specific searches that return
	    result sets of references and counts/stats for these result sets.
    """
    ####################
    # SQL fragments used to build up queries
    ####################
    SQLSEPARATOR = '||'
    LIT_TRIAGE_DATE = "10/31/2017"	# when we switched to new lit triage
    START_DATE = "10/01/2016" 		# earliest date for refs to get
					#  before lit Triage
    TUMOR_START_DATE = "07/01/2013"	# date to get add'l tumor refs from

    tmpTablesBuilt = False		# only build the tmp tables once

    #----------------
    # SQL to build tmp tables 
    #----------------
    BUILD_TMP_TABLES = [ \
	# tmp table of references w/ extracted text.
	# Need this tmp tble and indexes to make subsequent selects run fast.
    '''
	create temporary table tmp_refs
	as
	select distinct r._refs_key, r.creation_date
	from bib_refs r join bib_workflow_data bd on (r._refs_key =bd._refs_key)
	where bd.extractedtext is not null
    ''',
    '''
	create index tmp_idx2 on tmp_refs(_refs_key)
    ''',
	# this index is important for speed since bib_refs does not have an
	#  index on creation_date
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
    # SQL Parts for getting basic ref info (not extracted text)
    #----------------
    REFINFO_SELECT =  \
    '''
    select distinct r._refs_key,
	r.isdiscard, r.year,
	to_char(r.creation_date, 'MM/DD/YYYY') as "creation_date",
	r.isreviewarticle,
	typeTerm.term as ref_type,
	suppTerm.term as supp_status,
	r.journal, r.title, r.abstract,
	a.accid pubmed,
	bsv.ap_status,
	bsv.gxd_status, 
	bsv.go_status, 
	bsv.tumor_status, 
	bsv.qtl_status
    '''
    REFINFO_FROM =  \
    '''
    from bib_refs r join tmp_refs tr on (r._refs_key = tr._refs_key)
	join bib_workflow_data bd on (r._refs_key = bd._refs_key)
	join bib_status_view bsv on (r._refs_key = bsv._refs_key)
	join voc_term suppTerm on (bd._supplemental_key = suppTerm._term_key)
	join voc_term typeTerm on (r._referencetype_key = typeTerm._term_key)
	join acc_accession a on
	     (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
	      and a._mgitype_key=1 )
    '''
    RESTRICT_REF_TYPE = \
    '''
	and r._referencetype_key=31576687 -- peer reviewed article
	and r.isreviewarticle != 1
    '''
    #----------------
    # SQL Parts for getting extracted text parts so they can be catted together
    #----------------
    EXTTEXT_SELECT =  \
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
    # SQL Parts for getting stats/counts of references
    #----------------
    COUNT_SELECT = '    select count(distinct r._refs_key) as num\n'
    COUNT_FROM =  \
    '''
    from bib_refs r join tmp_refs tr on (r._refs_key = tr._refs_key)
	join bib_status_view bsv on (r._refs_key = bsv._refs_key)
    '''
    #-----------------------------------

    def __init__(self, args):
	self.args = args

    #@abstract
    def getName(self):
	return 'reference records from 1/1/2010' # example

    #@abstract
    def getWhereClauses(self):
	return 'where 1=0'

    #-----------------------------------

    def getCount(self):
	self.buildTmpTables()

	results = self.runSQL(self.buildCountSQL(),
				    'getting %s count' % self.getName())
	return results[-1][0]['num']
    #-----------------------------------

    def buildCountSQL(self):
	if self.args.restrictArticles:
	    restrict = self.RESTRICT_REF_TYPE
	else:
	    restrict = ''
	return self.COUNT_SELECT + self.COUNT_FROM + self.getWhereClauses() \
								     + restrict
    #-----------------------------------

    def getRefRecords(self):
	"""
	Run SQL for basic fields and extracted text fields, & join them.
	Return list of records.
	Each record represents one article w/ its basic fields & its
	extracted text.
	"""
	self.buildTmpTables()

	refQ, textQ = self.buildRefRecordsSQL()

	rslts = self.runSQL(refQ, 'getting ref info for %s' % self.getName())
	refRcds = rslts[-1]

	rslts = self.runSQL(textQ, 'getting extracted text for %s'  \
							    % self.getName())
	extTextRcds = rslts[-1]

	return self.joinExtractedText(refRcds, extTextRcds)
    #-----------------------------------

    def joinExtractedText(self, refRcds, extTextRcds):
	startTime = time.time()
	verbose( "Joining ref info to extracted text\n")

	extTextSet = ExtractedTextSet( extTextRcds )
	extTextSet.joinRefs2ExtText( refRcds, allowNoText=True )

	verbose( "%8.3f seconds\n\n" %  (time.time()-startTime))
	return refRcds
    #-----------------------------------

    def buildRefRecordsSQL(self, ):
	"""
	Assemble SQL statements (strings) to run to get samples from db.
	Return pair of SQL (basic fields query, ext text query)
	"""
	where   = self.getWhereClauses()

	if self.args.restrictArticles:
	    restrict = self.RESTRICT_REF_TYPE
	else:
	    restrict = ''

	if self.args.nResults > 0: limitSQL ="\nlimit %d\n" % self.args.nResults
	else: limitSQL = ''

	refInfoSQL = self.REFINFO_SELECT + self.REFINFO_FROM + where + \
							    restrict + limitSQL
	extTextSQL = self.EXTTEXT_SELECT + self.EXTTEXT_FROM + where + \
							    restrict + limitSQL
	return refInfoSQL, extTextSQL
    #-----------------------------------

    def buildTmpTables(self,):
	if not BaseRefSearch.tmpTablesBuilt:
	    results = self.runSQL(self.BUILD_TMP_TABLES, 'Building temp tables')
	    BaseRefSearch.tmpTablesBuilt = True
    #-----------------------------------

    def runSQL(self, sql, label):
	"""
	Run an SQL stmt and return results
	sql is list of SQLstmts or a single stmt (string)
	"""
	startTime = time.time()
	verbose(label + '...')
	if type(sql) == type(''):
	    results = db.sql( string.split(sql, self.SQLSEPARATOR), 'auto')
	else:
	    results = db.sql(sql, 'auto')
	verbose( "SQL time: %8.3f seconds\n" % (time.time()-startTime) )
	return results
    #-----------------------------------

# ------------------ end BaseRefSearch # }

class UnSelectedAfterRefSearch(BaseRefSearch):  # {
    """ IS: RefSearch for UNselected refs for a group after new littriage proces
    """
    def __init__(self, args, group, bsvFieldName):
	super(type(self), self).__init__(args)
	self.group = group
	self.bsvFieldName = bsvFieldName	# bib_stat_view field for group
    def getName(self):
	return '%s UNselected_after %s' % (self.group, self.LIT_TRIAGE_DATE)
    def getWhereClauses(self):
	return '''
    -- UNselected after
    where tr.creation_date > '%s'
    and ( (r.isdiscard = 1 and r._createdby_key != 1609) --not littriage_discard
	or bsv.%s = 'Rejected')
    ''' % (self.LIT_TRIAGE_DATE, self.bsvFieldName,)
	# really want: "r.isdiscard=1 and this discard was set by a curator"
	#   (rather than automated process),
	#   but db doesn't keep track of who set discard,
	#   so "not created by littriage_discard loader" is reasonable approx
# ----------- }

class SelectedAfterRefSearch(BaseRefSearch):  # {
    """ IS: RefSearch for selected refs for a group after new littriage proces
    """
    def __init__(self, args, group, bsvFieldName):
	super(type(self), self).__init__(args)
	self.group = group
	self.bsvFieldName = bsvFieldName	# bib_stat_view field for group
    def getName(self):
	return '%s selected_after %s' % (self.group, self.LIT_TRIAGE_DATE)
    def getWhereClauses(self):
	return '''
    -- selected after
    where tr.creation_date > '%s'
    and r.isdiscard = 0  -- likely unnec., but ensures sel and UNsel disjoint
    and bsv.%s in ( 'Chosen', 'Indexed', 'Full-coded')
    ''' % (self.LIT_TRIAGE_DATE, self.bsvFieldName)
# ----------- }

class GoSelectedAfterRefSearch(BaseRefSearch):  # {
    """ IS: RefSearch for selected refs for GO after new lit triage proces
    """
    def __init__(self, args,):
	super(type(self), self).__init__(args)
	self.group = 'GO'
	self.bsvFieldName = 'go_status'	# bib_stat_view field for group
    def getName(self):
	return '%s selected_after %s' % (self.group, self.LIT_TRIAGE_DATE)
    def getWhereClauses(self):
	return '''
    -- GO selected after
    where tr.creation_date > '%s'
    and r.isdiscard = 0  -- likely unnec., but ensures sel and UNsel disjoint
    and bsv.%s in ('Chosen', 'Indexed', 'Full-coded')
    and exists (select 1 from bib_workflow_status bs
	    where bs._refs_key = r._refs_key
	    and bs._group_key = 31576666		-- GO
	    and bs._status_key in (31576671, 31576673, 31576674)
				    -- Chosen, Indexed, Full-coded
	    and bs._createdby_key != 1571 -- pm2geneload
	    )
    ''' % (self.LIT_TRIAGE_DATE, self.bsvFieldName)
# ----------- }

class GoSelectedBeforeRefSearch(BaseRefSearch):  # {
    """ IS: RefSearch for selected refs for GO before new lit triage proces
    """
    def __init__(self, args, startDate=None):
	super(type(self), self).__init__(args)
	self.group = 'GO'
	self.bsvFieldName = 'go_status'	# bib_stat_view field for group
	self.startDate = startDate
    def getName(self):
	if self.startDate:
	    return '%s selected_before %s-%s' % \
			(self.group, self.startDate, self.LIT_TRIAGE_DATE)
	else:
	    return '%s selected_before %s' % (self.group, self.LIT_TRIAGE_DATE)
    def getWhereClauses(self):
	if self.startDate:
	    startDateClause = "and tr.creation_date >= '%s'" % self.startDate
	else:
	    startDateClause = ''
	return '''
    -- GO selected before
    where tr.creation_date <= '%s'
    and r.isdiscard = 0  -- likely unnec., but ensures sel and UNsel disjoint
    and bsv.%s in ('Chosen', 'Indexed', 'Full-coded')
    and exists (select 1 from bib_workflow_status bs
	    where bs._refs_key = r._refs_key
	    and bs._group_key = 31576666		-- GO
	    and bs._status_key in (31576671, 31576673, 31576674)
				    -- Chosen, Indexed, Full-coded
	    and bs._createdby_key != 1571 -- pm2geneload
	    )
    ''' % (self.LIT_TRIAGE_DATE, self.bsvFieldName) + startDateClause
# ----------- }

class SelectedBeforeRefSearch(BaseRefSearch):  # {
    """ IS: RefSearch for selected refs for a group before new littriage proces
    """
    def __init__(self, args, group, bsvFieldName, startDate=None):
	super(type(self), self).__init__(args)
	self.group = group
	self.bsvFieldName = bsvFieldName	# bib_stat_view field for group
	self.startDate = startDate
    def getName(self):
	if self.startDate:
	    return '%s selected_before %s-%s' % \
			(self.group, self.startDate, self.LIT_TRIAGE_DATE)
	else:
	    return '%s selected_before %s' % (self.group, self.LIT_TRIAGE_DATE)
    def getWhereClauses(self):
	if self.startDate:
	    startDateClause = "and tr.creation_date >= '%s'" % self.startDate
	else:
	    startDateClause = ''
	return '''
    -- selected before
    where 
     bsv.%s in ('Chosen', 'Indexed', 'Full-coded')
     and tr.creation_date <= '%s' -- before start date
    ''' % ( self.bsvFieldName, self.LIT_TRIAGE_DATE, ) + startDateClause
# ----------- }

dataSets = {
    'ap' :	{
	'unselected_after': UnSelectedAfterRefSearch(args,'AP','ap_status'),
	'selected_after'  : SelectedAfterRefSearch(args,'AP','ap_status'),
	'selected_before' : SelectedBeforeRefSearch(args,'AP','ap_status',
				    startDate='6/1/2015'),
	},
    'go' :	{
	'unselected_after': UnSelectedAfterRefSearch(args,'GO','go_status'),
	'selected_after'  : GoSelectedAfterRefSearch(args,),
	'selected_before' : GoSelectedBeforeRefSearch(args,startDate='1/1/2014'),
	},
    'gxd':	{
	'unselected_after': UnSelectedAfterRefSearch(args,'GXD','gxd_status'),
	'selected_after'  : SelectedAfterRefSearch(args,'GXD','gxd_status'),
	'selected_before' : SelectedBeforeRefSearch(args,'GXD','gxd_status'),
	},
    'tumor':	{
	'unselected_after': UnSelectedAfterRefSearch(args,'Tumor','tumor_status'),
	'selected_after' : SelectedAfterRefSearch(args,'Tumor','tumor_status'),
	'selected_before': SelectedBeforeRefSearch(args,'Tumor','tumor_status'),
	},
    }
#-----------------------------------

class ExtractedTextSet (object): # {
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
# end class ExtractedTextSet ----------------------------------- }

####################
def main():
####################

    verbose( "Hitting database %s %s as mgd_public\n" % (args.host, args.db))
    verbose( "Query option:  %s\n" % args.group)

    startTime = time.time()

    if args.counts:
	writeCounts(args)
    else:
	if args.restrictArticles:
	    verbose("Omitting review and non-peer reviewed articles\n")
	else:
	    verbose("Including review and non-peer reviewed articles\n")

	refSearch = dataSets[args.group].get(args.queryKey)
	if refSearch:
	    results = refSearch.getRefRecords()
	    n = writeSamples(results)
	    verbose("%d samples written\n" % n)
	else:
	    sys.stderr.write("'%s' is not a valid search for group %s\n" % \
						    (args.queryKey, args.group))
	    sys.stderr.write("Valid vals: %s\n" % str(dataSets[args.group].keys()))
	    return
    verbose( "Total time: %8.3f seconds\n\n" % (time.time()-startTime))
#-----------------------------------

def writeCounts(args):
    sys.stdout.write(time.ctime() + '\n')

    if args.restrictArticles:
	sys.stdout.write("Omitting review and non-peer reviewed articles\n")
    else:
	sys.stdout.write("Including review and non-peer reviewed articles\n")

    counts = []
    total  = 0
    searches = dataSets[args.group]

    for sName in sorted(searches.keys()):
	ds = searches[sName]
	count = ds.getCount()
	counts.append( {'name': ds.getName(), 'count': count} )
	total += count

    for countInfo in counts:
	percent = 100.0 * countInfo['count']/total
	sys.stdout.write("%-43s %d\t%4.1f%%\n" % \
			(countInfo['name'], countInfo['count'], percent))
    return
#-----------------------------------
    
def writeSamples(results	# list of records from SQL query (dicts)
    ):
    """
    Write records to stdout
    Return count of records written
    """
    sampleSet = sampleDataLib.ClassifiedSampleSet()

    for r in results:
	sampleSet.addSample( sqlRecord2ClassifiedSample(r) )

    sampleSet.write(sys.stdout, writeHeader=True)
    return len(results)
#-----------------------------------

def sqlRecord2ClassifiedSample( r,		# sql Result record
    ):
    """
    Encapsulates knowledge of ClassifiedSample.setFields() field names
    """
    newR = {}

    if r['isdiscard'] == 1:
	sampleClass = CLASS_NAMES[INDEX_OF_DISCARD]
    else:
	sampleClass = CLASS_NAMES[INDEX_OF_KEEP]

    newR['knownClassName']= sampleClass
    newR['ID']            = str(r['pubmed'])
    newR['creationDate']  = str(r['creation_date'])
    newR['year']          = str(r['year'])
    newR['journal']       = '_'.join(str(r['journal']).split(' '))
    newR['title']         = cleanUpTextField(r, 'title')
    newR['abstract']      = cleanUpTextField(r, 'abstract')
    newR['extractedText'] = cleanUpTextField(r, 'ext_text')
    newR['isReview']      = str(r['isreviewarticle'])
    newR['refType']       = str(r['ref_type'])
    newR['suppStatus']    = str(r['supp_status'])
    newR['apStatus']      = str(r['ap_status'])
    newR['gxdStatus']     = str(r['gxd_status'])
    newR['goStatus']      = str(r['go_status'])
    newR['tumorStatus']   = str(r['tumor_status']) 
    newR['qtlStatus']     = str(r['qtl_status'])

    return sampleDataLib.ClassifiedSample().setFields(newR)
#-----------------------------------

def cleanUpTextField(rcd,
		    textFieldName,
    ):
    # in case we omit this text field during debugging, check if defined
    if rcd.has_key(textFieldName): text = str(rcd[textFieldName])
    else: text = ''

    if args.maxTextLength:	# handy for debugging
	text    = text[:args.maxTextLength]

    text = removeNonAscii( cleanDelimiters( text))
    return text
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
	if True:
	    group = args.group
	    searches = dataSets[group]
	    for sName in searches.keys():
		print '---------------'
		ds = searches[sName]
		print ds.getName()
		print ds.buildCountSQL()
		refSQL, textSQL = ds.buildRefRecordsSQL()
		print refSQL
		print textSQL

	if False:	# debug SQL
	    for i, (b,t) in enumerate(buildGetSamplesSQL(args, )):
		print "%d:" % i
		print b
		print t
	if False:	# test ExtractedTextSet
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
