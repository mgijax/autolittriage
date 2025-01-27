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
import db
import utilsLib
import sampleDataLib
from ExtractedTextSet import ExtractedTextSet
#-----------------------------------

SAMPLE_OBJ_TYPE = sampleDataLib.CurGroupClassifiedSample
sampleSet = sampleDataLib.ClassifiedSampleSet(sampleObjType=SAMPLE_OBJ_TYPE)
# for the output delimited file
FIELDSEP     = SAMPLE_OBJ_TYPE.getFieldSep()
RECORDEND    = SAMPLE_OBJ_TYPE.getRecordEnd()

POS_CLASSNAME = SAMPLE_OBJ_TYPE.getClassNames()[SAMPLE_OBJ_TYPE.getY_positive()]
NEG_CLASSNAME = SAMPLE_OBJ_TYPE.getClassNames()[SAMPLE_OBJ_TYPE.getY_negative()]

#-----------------------------------

def getArgs():
    parser = argparse.ArgumentParser( \
        description='Get training samples for curation group select/unselect, write to stdout')

    parser.add_argument('--test', dest='test', action='store_true',
        required=False,
        help="just run ad hoc test code")

    parser.add_argument('--group', dest='group', action='store', required=True, 
        choices=['ap', 'gxd', 'go', 'tumor',], help='which curation group')

    parser.add_argument('--query', dest='queryKey', action='store',
        required=False, default='selected_after',
        choices=['unselected_after', 'selected_after', 'selected_before'],
        help='which subset of the ref samples to get, default: selected_after')

    parser.add_argument('--counts', dest='counts', action='store_true',
        required=False, help="don't get references, just get counts")

    parser.add_argument('-l', '--limit', dest='nResults',
        required=False, type=int, default=0, 		# 0 means ALL
        help="limit SQL to n results. Default is no limit")

    parser.add_argument('--textlength', dest='maxTextLength',
        type=int, required=False, default=None,
        help="only include 1st n chars of text fields & 1 rcd/line")

    parser.add_argument('--norestrict', dest='restrictArticles',
        action='store_false', required=False,
        help="include all articles, default: skip review and non-peer reviewed")

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    defaultHost = os.environ.get('PG_DBSERVER', 'bhmgidevdb01')
    defaultDatabase = os.environ.get('PG_DBNAME', 'prod')

    parser.add_argument('-s', '--server', dest='server', action='store',
        required=False, default=defaultHost,
        help='db server. Shortcuts:  prod, dev, test. (Default %s)' %
                defaultHost)

    parser.add_argument('-d', '--database', dest='database', action='store',
        required=False, default=defaultDatabase,
        help='which database. Example: mgd (Default %s)' % defaultDatabase)

    args =  parser.parse_args()

    if args.server == 'prod':
        args.host = 'bhmgidb01.jax.org'
        args.db = 'prod'
    elif args.server == 'dev':
        args.host = 'mgi-testdb4.jax.org'
        args.db = 'prod_dev'
    elif args.server == 'test':
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
        '%s' as "known_class_name",
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
    '''		# "known_class_name" is a constant determined by whether this
    		#    ref search returns positive or negative samples
                # Skipping suppTerm for now since in bib_workflow_data there
                #    are multiple records that don't always agree on the
                #    supplemental status term. If we include these, (1) we get
                #    multiple records returned in the join (2) would take some
                #    work to get the right status (the one associated with the
                #    extracted *body* text)
    REFINFO_FROM =  \
    '''
    from bib_refs r join tmp_refs tr on (r._refs_key = tr._refs_key)
        join bib_workflow_data bd on (r._refs_key = bd._refs_key)
        join bib_status_view bsv on (r._refs_key = bsv._refs_key)
        -- join voc_term suppTerm on (bd._supplemental_key = suppTerm._term_key)
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
        join acc_accession a on (r._refs_key = a._object_key
                and a._logicaldb_key = 29 and a._mgitype_key=1)
    '''
            # Need acc_accession join so we dont count refs that don't have
            #   pubmed IDs.
    #-----------------------------------

    def __init__(self,
        args,
        ispositive,	# True if refs from this search are in the pos class
        ):
        self.args = args
        self.knownClassName = self.determineKnownClassName(ispositive)

    def determineKnownClassName(self, ispositive):
        if ispositive:
            knownClassName = POS_CLASSNAME
        else:
            knownClassName = NEG_CLASSNAME
        return knownClassName

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

        # set constant field in the select clause for the known class name
        refInfoSelect = self.REFINFO_SELECT % self.knownClassName

        refInfoSQL = refInfoSelect + self.REFINFO_FROM + where + \
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
            results = db.sql(sql.split(self.SQLSEPARATOR), 'auto')
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
        super(type(self), self).__init__(args, False)
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
        super(type(self), self).__init__(args, True)
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
        super(type(self), self).__init__(args, True)
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
        super(type(self), self).__init__(args, True)
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
        super(type(self), self).__init__(args, True)
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
            sys.stderr.write("Valid vals: %s\n" % \
                                        str(list(dataSets[args.group].keys())))
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
    global sampleSet

    for r in results:
        sampleSet.addSample( sqlRecord2ClassifiedSample(r) )

    sampleSet.setMetaItem('host', args.host)
    sampleSet.setMetaItem('db', args.db)
    sampleSet.setMetaItem('time', time.strftime("%Y/%m/%d-%H:%M:%S"))
    sampleSet.write(sys.stdout, writeHeader=True, writeMeta=True)
    return len(results)
#-----------------------------------

def sqlRecord2ClassifiedSample( r,		# sql Result record
    ):
    """
    Encapsulates knowledge of ClassifiedSample.setFields() field names
    """
    newR = {}
    if str(r['isdiscard']) == '0':
        discardKeep = 'keep'
    else:
        discardKeep = 'discard'

    newR['knownClassName']= str(r['known_class_name'])
    newR['ID']            = str(r['pubmed'])
    newR['creationDate']  = str(r['creation_date'])
    newR['year']          = str(r['year'])
    newR['journal']       = '_'.join(str(r['journal']).split(' '))
    newR['title']         = cleanUpTextField(r, 'title')
    newR['abstract']      = cleanUpTextField(r, 'abstract')
    newR['extractedText'] = cleanUpTextField(r, 'ext_text') 
    if args.maxTextLength: newR['extractedText'] += '\n'
    newR['discardKeep']   = discardKeep
    newR['isReview']      = str(r['isreviewarticle'])
    newR['refType']       = str(r['ref_type'])
    newR['suppStatus']    = str(r['supp_status'])
    newR['apStatus']      = str(r['ap_status'])
    newR['gxdStatus']     = str(r['gxd_status'])
    newR['goStatus']      = str(r['go_status'])
    newR['tumorStatus']   = str(r['tumor_status']) 
    newR['qtlStatus']     = str(r['qtl_status'])

    return SAMPLE_OBJ_TYPE().setFields(newR)
#-----------------------------------

def cleanUpTextField(rcd,
                    textFieldName,
    ):
    # in case we omit this text field during debugging, check if defined
    if rcd.has_key(textFieldName):      # 2to3 note: keep this has_key() call
        text = str(rcd[textFieldName])
    else: text = ''

    if args.maxTextLength:	# handy for debugging
        text = text[:args.maxTextLength]
        text = text.replace('\n',' ')

    text = utilsLib.removeNonAscii( cleanDelimiters( text))
    return text
#-----------------------------------

def cleanDelimiters(text):
    """ remove RECORDEND and FIELDSEPs from text (replace w/ ' ')
    """
    new = text.replace(RECORDEND,' ').replace(FIELDSEP,' ')
    return new
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
        if True:                # debug SQL
            group = args.group
            searches = dataSets[group]
            for sName in searches.keys():
                print('---------------')
                ds = searches[sName]
                print(ds.getName())
                print(ds.buildCountSQL())
                refSQL, textSQL = ds.buildRefRecordsSQL()
                print(refSQL)
                print(textSQL)
