#!/usr/bin/env python2.7 
#
# rmReviews.py - remove review papers from input sample file
#  read sample articles from stdin (see sampleDataLib.py)
#  write sample articles to stdout (that are not review articles)
#
# Needs a file containing indications whether an article is a review article
#  "indications" come from MGI's "isReview" flag, Pubmed's review status, 
#  and a status set by looking for text in/near the abstract that indicates
#  the paper is a review.
#
import sys
import string
import os
import time
import argparse

#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='Read sample, rm review papers, Write to stdout')

#    parser.add_argument('inputFiles', nargs=argparse.REMAINDER,
#    	help='files of samples')

    parser.add_argument('inputFile', help='file of samples or -')

    parser.add_argument('-r', dest='reviewFile', action='store',
        required=True, 
        help='file containing review articles indications')

    parser.add_argument('--notextpred', dest='includeTextPred',
	action='store_false', required=False,
	help="do not use text predictions for review status (only pubmed)")

#    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
#	required=False, help="skip helpful messages to stderr")

    args = parser.parse_args()

    return args
#----------------------

class ReviewRcd (object):
    """
    Record to hold fields from article review predictions file
    Does: knows how to initialize itself from a line (record text)
    """
    def __init__(self, record):
        FIELDSEP = '|'

	(
	self.pubmedID,
	self.mgiReview,
	self.pubmedReview,
	self.textCheckReview,
	self.textCheckNote,
	self.textCheckText,
	self.journal)  = map(string.strip, record.split(FIELDSEP))

	# convert to Booleans
	self.mgiReview       = self.mgiReview.lower() == 'true'
	self.pubmedReview    = self.pubmedReview.lower() == 'true'
	self.textCheckReview = self.textCheckReview.lower() == 'true'

#----------------------
class ReviewChecker (object):
    """
    Reads review indication's file, builds dictionary.
    Provides isReview(pmid) method
    """
    def __init__(self, file, includeTextPred=True):
	""" Read article review predictions file
	    Build dict {pmid: ReviewRcd}
	"""
	recordSep = '\n'
	if type(file) == type(sys.stdin):
	    fp = file
	else:
	    fp = open(file, 'r')
	rcds = fp.read().split(recordSep)	# read/split all rcds

	del rcds[0]			# header line
	del rcds[-1]			# empty line at end after split()

	self.reviewRcds = {}
	for rcdLine in rcds:
	    rcd = ReviewRcd(rcdLine)
	    self.reviewRcds[rcd.pubmedID] = rcd

	self.includeTextPred = includeTextPred
    #----------------------

    def isReview(self, pubmedID):
	pmid = str(pubmedID)
	if self.reviewRcds.has_key(pmid):
	    rcd = self.reviewRcds[pmid]
	    isRev = rcd.mgiReview or rcd.pubmedReview or \
			(rcd.textCheckReview and self.includeTextPred)
	    return isRev
	else:
	    return False

#----------------------

args = parseCmdLine()

#----------------------
# Main prog
#----------------------
def main():

#    verbose("Removing review papers\n")
#    startTime = time.time()

    #############
    # Get review indications file
    revChecker = ReviewChecker(args.reviewFile, args.includeTextPred)

    #############
    # Get sample lib
    # extend path up multiple parent dirs, hoping we can import sampleDataLib
    sys.path = ['/'.join(dots) for dots in [['..']*i for i in range(1,4)]] + \
		    sys.path
    import sampleDataLib
    recordSep = sampleDataLib.RECORDSEP

    #############
    # Get/read sample file
    if args.inputFile == '-':
	fp = sys.stdin
    else:
	fp = open(args.inputFile, 'r')
    sampleRcds = fp.read().split(recordSep)	# read/split all rcds

    del sampleRcds[-1]			# empty line at end after split()

    sys.stdout.write(sampleRcds[0] + recordSep)	# headerline
    del sampleRcds[0]

    #############
    # Loop through samples, delete any that are review articles
    numPapers = len(sampleRcds)
    numSkipped = 0

    for rcd in sampleRcds:
	sr = sampleDataLib.SampleRecord(rcd)
	pmid = sr.getID()
	if revChecker.isReview(pmid):
	    numSkipped += 1
	    continue
	else:
	    sys.stdout.write( sr.getSampleAsText() )

    sys.stderr.write("Total articles: %d; Review articles skipped: %d\n" \
		    % (numPapers, numSkipped))

# ---------------------

def verbose(text):
    if args.verbose: sys.stderr.write(text)

# ---------------------
if __name__ == "__main__":
    main()
