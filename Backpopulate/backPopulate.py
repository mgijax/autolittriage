""" Author:  Jim, August 2018
    For specified journals, and other params (volume, issue, date range)
	get PDFs (and/or .xml) from PMC Eutils and Open Access (OA) search.
    Populate output directories with PDFs and .xml files

    Output: Status/summary messages to stdout
	    Populate output directories, one subdir for each journal processed.

    Here is what I think I know about PMC and Open Access (OA):
    * When you search PMC via eutils, get list of matching articles (XML).
    * Basic structure of article XML:
	* <front> meta-data, journal, vol, issue, IDs, article-title, abstract
	* <body> - optional. seems to be the marked up text of the article.
	    * various markups: figure, caption, section/section title...
	* <back> - optional. references, acknowledgements, ...
    * So in theory, if <body> exists, can get our extracted text from it + front
	I have a method for this below, but it needs more work, and I'm
	not sure it is the right way to go.
	This seems like it would be formatted/flow differently from our PDF
	extractor.  (although if we only look at title + abstract + figure text,
	this might be ok)
	So I think we should get PDFs so we can run them through our normal 
	    text extractor.
    * It may be that only OA articles have a <body>, I can't quite tell
    * I also looked at the bulk download of PMC extracted text.
	ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_bulk/
	The examples I looked at didn't have the title text. Although again,
	if we pull title + abstract from db/pubmed and fig text from downloaded
	files, this might be fine.
	Again, I'm not sure which articles have this PMC extracted text.
    * some OA articles also have PDF on the OA FTP site. Need to query the OA
	service to find the location on the FTP site
	https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/
    * some OA articles have the PDF stored directly, some have the PDF within
	a .tgz file (some have no PDF, but presumably XML <body> ?)

    * So Current Goal: for matching articles that are not in MGD already,
		    get PDF files, if any, and XML files, if they have <body>
"""

import sys
import os
import time
import argparse
import simpleURLLib as surl
import NCBIutilsLib as eulib
import xml.etree.ElementTree as ET
import runCommand
import Dispatcher
# --------------------------
# Journals/Search params
# --------------------------

# eutils PMC search clause to include only mice papers
MICE_CLAUSE = '(mice[Title] OR mice[Abstract] OR mice[Body - All Words])'

# eutils PMC search clause to restrict PMC search to open access articles
OPEN_ACCESS_CLAUSE = 'open access[filter]'

# Volumes earlier than 2016 should be up to date
DEFAULT_DATERANGE = '2010/01/01:2016/12/31'

def parseCmdLine():
    parser = argparse.ArgumentParser( \
	description= \
	'''Get text and PDF files for articles.
	   Except for -p, filenames are pubmed IDs.'
	'''
	)
    parser.add_argument('inputFiles', nargs=argparse.REMAINDER,
	help='files with journal names')

    parser.add_argument('-o', '--output', dest='basePath', action='store',
        required=False, default='.',
        help= "Dir to write to. Files are written to dir/journal. Default = .")

    parser.add_argument('-d', '--daterange', dest='dateRange', action='store',
        required=False, default=DEFAULT_DATERANGE,
        help="date range. Default: %s" % DEFAULT_DATERANGE)

    parser.add_argument('-j', '--journal', dest='journalName', action='store',
        required=False, default=None,
        help="only search for this specific journal.")

    parser.add_argument('-p', '--pmc', dest='pmcID', action='store',
        required=False, default=None,
        help="Skip journal search, just get PDF for pmcID (no 'PMC').")

    parser.add_argument('--pubmed', dest='pubmedFile', action='store',
        required=False, default='mgiPubmedIDs.tsv',
        help="file containing pubmed IDs already in MGI.")

    parser.add_argument('--nonMice', dest='miceOnly',
        action='store_false', required=False, 
        help='include non-mice papers in searches. Default: mice only.')

    parser.add_argument('-m', '--maxFiles', dest='maxFiles', action='store',
        required=False, default=0, type=int,
        help="max num of articles to download.")

    parser.add_argument('--noWrite', dest='writeFiles',
        action='store_false', required=False, 
        help="don't write any files or directories.")

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
	help='print more messages')

    args = parser.parse_args()

    return args
# --------------------------

def buildJournalSearch(queryStrings, files, journal=None):
    """ return a { journalName : [ query strings ], ... }
	queryStrings = [ queryString, ... ]
	files = [ filenames to read journalNames from]
	journal= overides files, just do this journal
    """
    journalsToSearch = {}
    if journal != None:
	journalsToSearch[journal.strip()] = queryStrings
    else:
	for file in files:
	    fp = open(file, 'r')
	    journals = fp.readlines()

	    for j in journals:
		journalsToSearch[j.strip()] = queryStrings
    return journalsToSearch

# --------------------------
# Main routine
# --------------------------
def process():

    #global journalsToSearch
    args = parseCmdLine()

    if args.pmcID:		# just get pdf for this article and quit
	url = getPdfUrl(args.pmcID)
	if url != '':
	    getOpenAccessPdf(url, args.basePath, 'PMC'+str(args.pmcID)+'.pdf')
	return

    # just one query string per journal for now
    queryStrings = [ "%s[DP] AND %s" % (args.dateRange, OPEN_ACCESS_CLAUSE) ]

    journalsToSearch = buildJournalSearch(queryStrings, args.inputFiles,
					    journal=args.journalName)
    startTime = time.time()

    if args.miceOnly:		# add mice-only clause to each search
	for j, paramList in journalsToSearch.items():
	    journalsToSearch[j] = [ "%s AND %s" % (p, MICE_CLAUSE)
							for p in paramList ]
    # Find/write output files & get one (summary) reporter for each
    #   journal/search params
    pr = PMCfileRangler(basePath=args.basePath, pubmedFile=args.pubmedFile,
			    verbose=args.verbose, writeFiles=args.writeFiles)

    reporters = pr.downloadFiles(journalsToSearch, maxFiles=args.maxFiles)

    numPdfs = 0
    print
    for r in reporters:
	print r.getReport()
	numPdfs += r.getNumMatching()

    print
    print "Total PDFs Written: %d" %  numPdfs
    progress( 'Total time: %8.2f seconds\n' % (time.time() - startTime) )
    return
# --------------------------
# Classes
# --------------------------

class PMCarticle (object):
    """ PMC article record
    """
    pass
# --------------------------

class PMCsearchReporter (object):
    """ Class that keeps track of counts/stats for a given journal and search
    """
    def __init__(self,
	journal,		# the journal...
	searchParams,		# ... and search Params to report on
	count,			# num of articles matched by this search
	maxFiles=0,		# max files from search to process, 0=all
	):
	self.journal = journal
	self.searchParams = searchParams
	self.totalSearchCount = count
	self.maxFiles = maxFiles

	self.nResultsProcessed = 0	
	self.nResultsGotText = 0	# num extracted text files written
	self.nResultsGotPdf = 0		# num PDF files written
	self.nResultsGotXml = 0		# num XML files written

	self.skippedArticles = {}	# dict of skipped because wrong type
					# {"new type name" : [ pmIDs w/ type] }
	self.nSkipped = 0		# num articles skipped

	self.newTypes = {}		# dict of article types found
					#   that we haven't seen before
					# {"new type name" : [ pmIDs w/ type] }
	self.nWithNewTypes = 0		# num articles w/ new types

	self.noPdf = []			# [pmIDs] w/ no PDF we could find
	self.noXmlBody = []		# [pmIDs] w/ no <body> in XML
	self.mgiPubmedIds=[]		# [pmIDs] skipped since in MGI
	self.noPubmedIds=[]		# [pmcIDs] skipped since no PMID
    # ---------------------

    def skipArticle(self, article,):
	""" Record that this article has been skipped because of its type
	"""
	self.nSkipped += 1
	t = article.type
	if not self.skippedArticles.has_key(t):
	    self.skippedArticles[t] = []
	self.skippedArticles[t].append(article.pmid)

    def newType(self, article):
	""" Record that we found a new article type that we haven't seen before
	"""
	self.nWithNewTypes += 1
	t = article.type
	if not self.newTypes.has_key(t):
	    self.newTypes[t] = []
	self.newTypes[t].append(article.pmid)

    def gotText(self, article):
	""" Record that we got/wrote a text file for this article """
	self.nResultsGotText += 1

    def gotXml(self, article):
	""" Record that we got/wrote a XML file for this article """
	self.nResultsGotXml += 1

    def gotPdf(self, article):
	""" Record that we got/wrote a PDF file for this article """
	self.nResultsGotPdf += 1

    def gotNoPdf(self, article):
	""" couldn't get PDF url for this article """
	self.noPdf.append(article.pmid)

    def gotNoBody(self, article):
	""" no <body> tag for this article - hence, no text """
	self.noXmlBody.append(article.pmid)

    def gotNoPmid(self, article):
	""" couldn't get PMID for this article """
	self.noPubmedIds.append(article.pmcid)

    def skipInMgi(self, article):
	""" no <body> tag for this article - hence, no text """
	self.mgiPubmedIds.append(article.pmid)

    def getNumMatching(self):
	tot = self.totalSearchCount - self.nSkipped -self.nWithNewTypes \
	    - len(self.mgiPubmedIds) - len(self.noPdf) - len(self.noPubmedIds)
	return tot

    def getReport(self):
	# for now
	output = "Journal: %s\n'%s'\n" % (self.journal, self.searchParams)

	output += "%6d %s articles matched search:\n" % \
			    (self.totalSearchCount, self.journal[:25], )
	if self.totalSearchCount == 0: return output

	output += "%6d maxFiles\n" % self.maxFiles
	output += "%6d .txt files written\n" % self.nResultsGotText
	output += "%6d .xml files written\n" % self.nResultsGotXml
	output += "%6d .pdf files written\n" % self.nResultsGotPdf

	if self.nSkipped > 0:
	    output += "%6d Articles skipped because of type\n" % self.nSkipped
	    for t in self.skippedArticles.keys():
		output += "\t%6d type: %s\n" % (len(self.skippedArticles[t]), t)

	if self.nWithNewTypes > 0:
	    output += "%6d Articles w/ new types\n" % self.nWithNewTypes
	    for t in self.newTypes.keys():
		output += "\t%6d with type: %s, example: %s\n" % \
			( len(self.newTypes[t]), t, str(self.newTypes[t][0]) )

	if len(self.noPubmedIds) > 0:
	    output += "%6d Articles skipped since no PMID:\n" % \
					    len(self.noPubmedIds)
	    output += '\tPMC'+', '.join(map(str, self.noPubmedIds[:6])) + '\n'

	if len(self.mgiPubmedIds) > 0:
	    output += "%6d Articles skipped since in MGI:\n" % \
							len(self.mgiPubmedIds)
	    output += '\tPMID'+', '.join(map(str, self.mgiPubmedIds[:6])) + '\n'

	if len(self.noPdf) > 0:
	    output += "%6d Articles w/ no PDFs:\n" % len(self.noPdf)
	    output += '\tPMID' + ', '.join( map(str, self.noPdf[:6]) ) + '\n'

	if len(self.noXmlBody) > 0:
	    output += "%6d Articles w/ no body:\n" % len(self.noXmlBody)
	    output += '\tPMID' + ', '.join( map(str, self.noXmlBody[:6]) )+ '\n'
	return output

    def getReportHeader(self):
	# for now
	return ''
# end class PMCsearchReporter ------------------------

class PMCfileRangler (object):
    """ Knows how to query PMC and download PDFs from PMC OA FTP site
	Stores files in directories named by journal name.
	Also supports downloading full text XML files and text that PMC
	has extracted. But we are not using those for now (just PDFs)
    """
    # Article Types we know about, ==True if we want these articles,
    #  ==False if we don't
    # These values are taken from "article-type" attribute of <article>
    #  tag in PMC eutils fetch output
    articleTypes = {'research-article': True,
			'review-article': False,
			'other': False,
			'correction': False,
			'editorial': False,
			'article-commentary': False,
			'brief-report': False,
			'case-report': False,
			'letter': False,
			'discussion': False,
			'retraction': False,
			'oration': False,
			'reply': False,
			'news': False,
			}

    def __init__(self, 
		basePath='.',		# base path to write article files
					# files written to basePath/journalName
		urlReader=surl.ThrottledURLReader(seconds=0.2),
		pubmedFile='mgiPubmedIDs.tsv', # holds pubmed IDs in MGI
		verbose=False,
		writeFiles=True,	# =False to not write any files/dirs
		getXml=False,		# =True to write xml output for each
					#   matching article (pmid.xml)
		getPdf=True,		# =True to write PDF files for each
					#   matching article that has PDF
					#   (pmid.pdf)
		getText=False,		# =True to write extracted text file
					#   for each matching article that
					#   has text in the xml output: pmid.txt
		):
	self.basePath = basePath
	self.urlReader = urlReader
	self._getPubmedIds(pubmedFile)
	self.verbose = verbose
	self.writeFiles = writeFiles
	self.getXml = getXml
	self.getPdf = getPdf
	self.getText = getText

	self.journalSummary = {}
	self.curOutputDir = ''
	self.reporters = []
	self.curReporter = None		# current reporter (for journal/search)
    # ---------------------

    def _getPubmedIds(self, filename):
	""" read in MGI pubmed ID file, populate self.mgiPubmedIds
	"""
	fp = open(filename, 'r')
	self.mgiPubmedIds = {}
	fp.next()		# skip file header line
	for line in fp:
	    id, hasPdf, year, journal = line.split('\t')
	    self.mgiPubmedIds[id] = hasPdf

	fp.close()
    # ---------------------

    def downloadFiles(self,
		    journalSearch,	# {journalname: [search params]}
					#   search param is PMC query string,
					#   typically specifying vol/issue
					#   or date range
		    maxFiles=0,		# max number of matching files to
		    			#  actually download and store. 0=all
		    ):
	""" Search all the journals and all their search params.
	    Saving files as we go.
	    Return a list of PMCsearchReporters, one for each journal/params
		combination.
	"""
	for journal in sorted(journalSearch.keys()):
	    self._createOutputDir(journal)

	    for searchParams in journalSearch[journal]:
		progress("Searching %s %s..." % (journal, searchParams[:25]))
		startTime = time.time()
		count, resultsE, results = self._runSearch(journal,
						    searchParams, maxFiles)
		searchEnd = time.time()
		progress('%d results.\nSearch time: %8.2f\n' % \
				    (count, searchEnd-startTime))

		self.curReporter = PMCsearchReporter(journal, searchParams,
							    count, maxFiles)
		self.reporters.append(self.curReporter)

		self._processResults(journal, resultsE, results)
		processEnd = time.time()
		progress('\nProcess time: %8.2f\n' % (processEnd-searchEnd))

	return self.reporters
    # ---------------------

    def _runSearch(self, journalName, searchParams, maxFiles):
	""" Search PMC for articles from JournalName w/ search Params.
	    Return count of articles, ElementTree, and raw result text
		of PMC search results.
	"""
	query = '"%s"[TA]+AND+%s' % (journalName, searchParams,)
	query = query.replace(' ','+')

	# Search PMC for matching articles
	count, results, webenvURLParams = eulib.getSearchResults("PMC",
				    query, op='fetch', retmax=maxFiles,
				    URLReader=self.urlReader, debug=False )
	# JIM: check for and do something about errors and empty search rslts?
	#  (zero seems to work ok as is)

	#if self.verbose: progress( "'%s': %d PMC articles\n" % (query, count))

	resultsE = ET.fromstring(results)
	return count, resultsE, results
    # ---------------------

    def _processResults(self,
			journalName,
			resultsE,	# ElementTree of results
			results,	# raw return from eutils search
			):
	""" Process the results of the search.
	    For each article in the results, 
		parse the XML and pull out relevant bits.
		Skip the article if it not of the right type.
		Write out the requested files (xml, text, pdf)
	"""
	self.dispatcher = Dispatcher.Dispatcher(maxProcesses=5)
	self.cmdIndexes = []
	self.cmds = []
	self.articles = []

	for i, artE in enumerate(resultsE.findall('article')):
	    
	    # fill an article record with the fields we care about
	    art = PMCarticle()
	    art.journal = journalName
	    art.type = artE.attrib['article-type']

	    artMetaE = artE.find("front/article-meta")

	    art.pmcid  = artMetaE.find("article-id/[@pub-id-type='pmc']").text
	    art.pmid   = artMetaE.find("article-id/[@pub-id-type='pmid']")
	    if art.pmid == None:
		#print "Cannot find PMID for PMC %s, skipping" % str(art.pmcid)
		self.curReporter.gotNoPmid(art)
		continue
	    art.pmid   = artMetaE.find("article-id/[@pub-id-type='pmid']").text

	    if not self._wantArticle(art): continue

	    # write files
	    if self.getPdf:	self._queuePdfFile(art, artE)
	    if self.getXml:  	self._writeXmlFile(art, artE)
	    if self.getText:	self._writeTextFile(art, artE)
	# To use dispatcher, would need to save PDF requests and submit them
	#  to a batch PDF method
	self._runPdfQueue()
	return
    # ---------------------

    def _runPdfQueue(self, ):
	""" would be nice to factor out into a separate class
	"""
	self.dispatcher.wait()

	for i in range(len(self.cmds)):
	    idx = self.cmdIndexes[i]
	    article = self.articles[i]
	    gotFile = checkPdfCmd( self.cmds[i],
				    self.dispatcher.getReturnCode(idx),
				    self.dispatcher.getStdout(idx),
				    self.dispatcher.getStderr(idx), )
	    if gotFile:
		self.curReporter.gotPdf(article)
		if self.verbose: progress('P')	# output progress P
	    else:
		self.curReporter.gotNoPdf(article)
		if self.verbose: progress('p')
	return
    # ---------------------

    def _queuePdfFile(self, article, artE):

	linkUrl = getPdfUrl(article.pmcid)	# this is slow!

	if linkUrl == '':
	    self.curReporter.gotNoPdf(article)
	    if self.verbose: progress('p')
	    return

	if not self.writeFiles: return	# don't really output

	cmd = getPdfCmd( linkUrl, self.curOutputDir, 
				    'PMC' + str(article.pmcid) + '.pdf')

	#if self.verbose: progress('\n' + cmd + '\n')

	idx = self.dispatcher.schedule(cmd)
	self.cmdIndexes.append(idx)
	self.cmds.append(cmd)
	self.articles.append(article)
	return
    # ---------------------
   
    def _writeXmlFile(self, article, articleE):
	""" write articleE element XML to a filename based on pubmed ID
	"""
	bodyE = articleE.find("body")
	if bodyE == None:
	    self.curReporter.gotNoBody(article)
	    if self.verbose: progress('x')
	if not self.writeFiles: return

	fileName = 'PMC' + str(article.pmcid) + ".xml"
        pathName = os.sep.join( [ self.curOutputDir, fileName ] )

	with open(pathName, 'w') as fp:
	    fp.write( ET.tostring(articleE, method='xml'))
	    self.curReporter.gotXml(article)
	    if self.verbose: progress('X')
    # ---------------------
   
    def _writeTextFile(self, article, articleE):
	""" generate text from articleE element and write it to a filename
	    based on pubmed ID.
	"""
	bodyE = articleE.find("body")
	if bodyE == None:
	    self.curReporter.gotNoBody(article)
	    if self.verbose: progress('t')
	if not self.writeFiles: return

	#fileName = PMID_FILE_PREFIX + str(article.pmid) + ".txt"
	fileName = 'PMC' + str(article.pmcid) + ".txt"
        pathName = os.sep.join( [ self.curOutputDir, fileName ] )

	text = ''
	for e in articleE.itertext():
	    text += e
	
	with open(pathName, 'w') as fp:
	    fp.write(removeNonAscii(text))
	    self.curReporter.gotText(article)
	    if self.verbose: progress('T')
    # ---------------------

    def _wantArticle(self, article):
	""" Return True if we want this article (for now, we want its type)
	    Need to add check for already in MGD.
	"""
	if self.mgiPubmedIds.has_key(article.pmid):
	    self.curReporter.skipInMgi(article)
	    return False

	if self.articleTypes.has_key(article.type):	# know this type
	    if not self.articleTypes[article.type]:	# but don't want it
		self.curReporter.skipArticle(article)
		return False
	else:	# not seen this before. Report so we can decide if we want it
	    self.curReporter.newType(article)
	    return False
	return True
    # ---------------------

    def _createOutputDir(self, journalName):
	""" create an output directory for this journalName
	"""
        journal = '_'.join( journalName.split(' ') )
        self.curOutputDir = os.sep.join( [ self.basePath, journal ] )

	if not self.writeFiles: return
	
        if not os.path.exists(self.curOutputDir):
            os.makedirs(self.curOutputDir)
    # ---------------------
# --------------------------

def getPdfUrl_grep(pmcid):
    """ I TRIED THIS, BUT IT IS REALLY SLOW compared to using the api call
	Return the Open Access URL (str) to the pdf or gzipped tar file
	containing pdf for the given pmcid.
	Return '' if there is no such file
    """
    oaPdfIndex = "oa_non_comm_use_pdf.txt"
    oaTgzIndex = "oa_file_list.txt"
    baseUrl = 'ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/'

    # build grep commands
    findPdfCommand = "fgrep 'PMC%s' %s" % (str(pmcid), oaPdfIndex)
    findTgzCommand = "fgrep 'PMC%s' %s" % (str(pmcid), oaTgzIndex)

    # run to find ftp location of .pdf
    stdout, stderr, retcode = runCommand.runCommand(findPdfCommand)

    if retcode == 0:		# found the .pdf file location
	parts = stdout.split('\t')
	ftpPath = parts[0]
    else:
	# run to find ftp location of .tgz
	stdout, stderr, retcode = runCommand.runCommand(findTgzCommand)
	if retcode == 0:	# found the .tgz file location
	    parts = stdout.split('\t')
	    ftpPath = parts[0]
	else:
	    print "Cannot find ftp location for PMC%s" % str(pmcid)
	    return ''
    print "Ftp: %s" % ftpPath
    return baseUrl + ftpPath
# ---------------------

def getPdfUrl(pmcid):
    """ Return the Open Access URL (str) to the pdf or gzipped tar file
	containing pdf for the given pmcid.
	Return '' if there is no such file
    """
    # Can add "format=pdf" to oa search
    # Not sure if this means "has a free standing PDF" or "has a PDF either
    #  free standing or within a .tgz"
    # Should we only get articles that have PDFs?

    # get FTP file location on OA FTP site
    baseUrl = 'https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC%s'
    url = baseUrl % str(pmcid)
    out = surl.readURL(url)	 # no throttle req't for OA, so no throttle 
    #out = self.urlReader.readURL(url)
    ele = ET.fromstring(out)

    errorE = ele.find('./error')
    if errorE != None:
	code = errorE.attrib['code']
	msg = errorE.text
	print "Error finding OA link for PMC%s. Code='%s'. Message='%s'" \
					    % (pmcid, code, msg)
	return ''

    # Get file URL. Use PDF link if it exists, if not assume tgz link exists
    linkE = ele.find('./records/record/link/[@format="pdf"]')
    if linkE == None:		# no direct PDF link
	linkE = ele.find('./records/record/link/[@format="tgz"]')
	# Seems like this could fail, or could find .tgz but no PDF within
    #else: print "PMC%s had direct pdf link" % str(pmcid)

    return linkE.attrib['href']
# ---------------------

def getPdfCmd(linkUrl,	# URL to download from
    outputDir,			# directory where to store the file
    fileName,			# file name itself (presumably with .pdf)
    ):
    """ Return Unix command to Download the PDF at url.
    """
    # set up for Jon's cool download script (modified a bit) to get the PDF
    cmd = "./download_pdf.sh %s %s %s" % (linkUrl, outputDir, fileName)
    return cmd
# ---------------------

def checkPdfCmd(cmd,	# the command itself
    retcode,
    stdout,
    stderr,
    ):
    """ Check the retcode and stdout, stderr for this command.
	Report if there are any problems
	Return true if all ok.
    """
    if retcode != 0:
	print "Error on pdf download"
	print "retcode %d on: '%s'" % (retcode, cmd)
	if stdout[0] == "Error: no PDF found in gzip file\n":
	    print "stdout from cmd: Error: no PDF found in gzip file"
	else:
	    print "stdout from cmd: '%s'" % stdout
	    print "stderr from cmd: '%s'" % stderr
	return False
    return True
# ---------------------

def getOpenAccessPdf(linkUrl,   # URL to download from
    outputDir,                  # directory where to store the file
    fileName,                   # file name itself (presumably with .pdf)
    ):
    """ Download the PDF at url.
        Return True if we got the file ok, False, ow.
    """
    # set up for Jon's cool download script (modified a bit) to get the PDF
    cmd = getPdfCmd(linkUrl, outputDir, fileName)

    stdout, stderr, retcode = runCommand.runCommand(cmd) # uses curl

    return checkPdfCmd(cmd, retcode, stdout, stderr)
# ---------------------

# --------------------------
# helper routines
# --------------------------

def getTagStructure(e, n=2, indent=0, ):  # e is ElementTree element
    """ return string showing n levels deep so we can get a high level view of
	the element's structure
    """
    output = " " * indent + e.tag + str(e.attrib) + '\n'
    if n == 0 or len(e) == 0: return output
    for subE in e:
	output += getTagStructure(subE, n-1, indent=indent+2,)
    return output
# --------------------------

def removeNonAscii(text):
    """ return a string with all the non-ascii characters in text replaced
	by a space.
	Gets rid of those nasty unicode characters.
    """
    return  ''.join([i if ord(i) < 128 else ' ' for i in text])
# ---------------------

def progress(s):
    ''' write some progress info'''
    sys.stdout.write(s)
    sys.stdout.flush()
# ---------------------


if __name__ == "__main__": 
    process()
