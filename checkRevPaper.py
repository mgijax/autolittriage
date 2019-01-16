#!/usr/bin/env python2.7 
#
# Look for review papers
#
# Output to stdout.
#
import sys
import string
import os
import time
import argparse
import json
import simpleURLLib as surl
import NCBIutilsLib as eulib

DEFAULT_STATUS_FILE     = 'refStatuses.txt'
DEFAULT_PREDICTION_FILE = '_test_pred.txt'
PREDFILE_RECORDSEP = '\n'

#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='Compute recall value for each curation group. Write to stdout')

    #parser.add_argument('statusFile', help='file of paper curation statuses')
    #parser.add_argument('predictionFile', help='file of paper predictions')

    parser.add_argument('-l', '--long', dest='longOutput', action='store_true',
	required=False,
	help="long output. Write each prediction + paper statuses")

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
	required=False, help="skip helpful messages to stderr")

    args = parser.parse_args()
    args.longOutputFile = sys.stdout

    return args
#----------------------

args = parseCmdLine()

# maybe should be using sampleDataLib to parse full raw records...
#----------------------
class Paper (object):
    """
    Is a paper
    Does: knows how to initialize itself from a line (record text)
    """
    def __init__(self, record):
	FIELDSEP = '|'	
	(self.pubmedID,
	self.journal,
	) = map(string.strip, record.split(FIELDSEP))

	self.mgiReview = False		# for now, only working on non-reviews
	self.pubmedReview = False
	self.textCheckReview = False

#----------------------

def getPapers(papersFile):
    """ Read the file of papers: pubmed IDs and journal
	Return [ Paper objects ]
    """
    RECORDSEP = '\n'
    if type(papersFile) == type(sys.stdin):
	fp = papersFile
    else:
	fp = open(papersFile,'r')

    rcds = fp.readlines()
    del rcds[0] 			# header line
    papers = []
    for rcd in rcds:
	paper = Paper(rcd.strip().lower())
	papers.append(paper)

    return papers
#----------------------

#----------------------
# Main prog
#----------------------
def main():
    papers = getPapers(sys.stdin)

    testnum = 1040
#    papers = papers[:testnum]
    setPubmedReview(papers)
#    setTextCheckReview(papers)
    outputResults(papers)

# ---------------------

def setPubmedReview(allPapers):

    urlReader = surl.ThrottledURLReader( seconds=0.4 ) # don't overwhelm eutils
    numPerPost = 500				# keep each post reasonable

    pmid = "no pubmed ID yet"	# keep current pmid to print if exception
    try:
	for start in range(0, len(allPapers), numPerPost):
	    verbose('..%d' % start)
	    last = start + numPerPost
	    papers = allPapers[start:last]		# in this batch
	    pubmedIDs = [ p.pubmedID for p in papers ]
	    resultsStr = eulib.getPostResults('pubmed', pubmedIDs,
					    URLReader = urlReader, op='summary',
					    rettype=None, retmode='json',) [0]
	    resultsJson = json.loads(resultsStr)
	    for paper in papers:
		pmid = paper.pubmedID
		r = resultsJson['result'][pmid]
		try:
		    paper.pubmedReview = isPubmedReview(r)
		except:
		    sys.stderr.write("\nException: %s\n" % str(pmid))
		    sys.stderr.write(json.dumps(r,sort_keys=True,indent=4,
						    separators=(',',': '))
						    + '\n')
		    continue
    except:
	sys.stderr.write("\nBatch start: %d\n" % start)
	raise
# ---------------------

def isPubmedReview(paperJson):
    """ Return true iff the paper has type "review"
    """
    return 'review' in map( lambda x: str(x).lower(),  paperJson['pubtype'] )
# ---------------------

def setTextCheckReview(papers):
    """ set p.textCheckReview for each p in papers
	Need journal, abstract, extracted text - think about text & abstract
	I stripped these already
    """
    for p in papers:
	p.textCheckReview = False	# for now
# ---------------------

def outputResults( papers,
		):
    """
    """
    pmNotMgi = 0
    for p in papers:
	if not p.mgiReview and p.pubmedReview: pmNotMgi += 1
    sys.stderr.write("\nOut of %d papers, review in pubmed but not MGI: %d\n" \
						% (len(papers), pmNotMgi) )

    SEP = '|'
    sys.stdout.write( SEP.join( [ \
	'PMID',
	'MGI review',
	'Pubmed Review',
	'Text check Review',
	'Journal',
	] ) + '\n' )

    for p in papers:
	sys.stdout.write( SEP.join( [ \
		    str(p.pubmedID),
		    str(p.mgiReview),
		    str(p.pubmedReview),
		    str(p.textCheckReview),
		    p.journal,
		    ] ) + '\n' )
# ---------------------

def outputLongHeader():
    """
    Write header line for long output file
    """
    args.longOutputFile.write( Prediction.FIELDSEP.join( [ \
		'ID',
		'True Class',
		'Pred Class',
		'FP/FN',
		'Confidence',
		'Abs Value',
		'ap_status',
		'gxd_status',
		'go_status',
		'tumor_status',
		'qtl_status',
		] ) + PREDFILE_RECORDSEP )
# ---------------------

def verbose(text):
    if args.verbose: sys.stderr.write(text)
# ---------------------

if __name__ == "__main__":
    main()
