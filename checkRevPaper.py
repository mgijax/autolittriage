#!/usr/bin/env python2.7 
#
# Look for review papers
# Read from stdin
# Output to stdout.
#
import sys
import string
import os
import time
import argparse
import json
import sampleDataLib as sdlib
import simpleURLLib as surl
import NCBIutilsLib as eulib
from basicLib import sublistFind

DEFAULT_STATUS_FILE     = 'refStatuses.txt'
DEFAULT_PREDICTION_FILE = '_test_pred.txt'
PREDFILE_RECORDSEP = '\n'

#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description=
    '''Compare paper Review status from MGI/Pubmed/text heuristic.
    Read doc sample records from stdin. Output to stdout'''
    )

    #parser.add_argument('statusFile', help='file of paper curation statuses')
    #parser.add_argument('predictionFile', help='file of paper predictions')

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
	required=False, help="skip helpful messages to stderr")

    args = parser.parse_args()
    return args
#----------------------

args = parseCmdLine()

#----------------------
class SimplePaper (object):
    """
    CURRENTLY, NOT USED. Replaced by Paper class.
    Is a paper. Only with pubmed ID and journal
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
# use sampleDataLib to parse full raw records...
class Paper (sdlib.SampleRecord):
    """
    Is a paper. From full sample record file (see sampleDataLib.py)
    Does: knows how to initialize itself from a line (record text)
    """
    def __init__(self, record):
	super(type(self), self).__init__(record)

	self.pubmedID = self.ID

	self.mgiReview       = False	# Review status in MGI
					# For now, only working on non-reviews
					# Will need to get this from sample
					#  rcd if we start getting rev papers
	self.pubmedReview    = False	# Review status in pubmed
	self.textCheckReview = False	# Review prediction from text heuristic
	self.textCheckNote = ''		#  Reason/note from heuristic
	self.textCheckText   = ''	# Additional, surrounding text

#----------------------

def getPapers(papersFile):
    """ Read the file of papers: pubmed IDs and journal
	Return [ Paper objects ]
    """
#    RECORDSEP = '\n'
    RECORDSEP = ';;'
    if type(papersFile) == type(sys.stdin):
	fp = papersFile
    else:
	fp = open(papersFile,'r')

    rcds = fp.read().split(RECORDSEP)
    del rcds[0] 			# header line
    del rcds[-1]			# empty line after split
    papers = []
    for rcd in rcds:
	paper = Paper(rcd)
	papers.append(paper)

    return papers
#----------------------

#----------------------
# Main prog
#----------------------
def main():
    papers = getPapers(sys.stdin)

#    testnum = 2000
#    papers = papers[:testnum]
    setPubmedReview(papers)
    setTextCheckReview(papers)
    outputResults(papers)

# ---------------------

def setPubmedReview(allPapers):
    """
    For each paper in allPapers, set paper.pubmedReview to True
	if Pubmed says it is a review paper (False otherwise)
    """
    urlReader = surl.ThrottledURLReader( seconds=0.4 ) # don't overwhelm eutils
    numPerPost = 500	# keep each post reasonable. (500 only for json output)

    try:
	for start in range(0, len(allPapers), numPerPost): # break into batches
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
		try:
		    r = resultsJson['result'][pmid]
		    paper.pubmedReview = isPubmedReview(r)
		except:		# report which pmid we had trouble with
		    sys.stderr.write("\nException: PMID %s\n" % str(pmid))
		    sys.stderr.write(json.dumps(r,sort_keys=True,indent=4,
						    separators=(',',': '))
						    + '\n')
		    continue
    except:		# report some info so we might find the offending paper
	sys.stderr.write("\nBatch start: %d\n" % start)
	raise
    return
# ---------------------

def isPubmedReview(paperJson):
    """ Return True iff the paper has type "review"
	paperJson is the json record for a paper from pubmed summary rcd
	paperJson['pubtype'] is a list of pubmed pubtypes, 'review' may be one
    """
    return 'review' in map( lambda x: str(x).lower(),  paperJson['pubtype'] )
# ---------------------

def setTextCheckReview(allPapers):
    """
    For each paper in allPapers, set paper.textCheckReview to True
	if the paper appears to be a review paper based on words in the
	extractedText.
    ALSO SET paper.textCheckNote, paper.textChecktext
    """
    for p in allPapers:
	p.textCheckReview, p.textCheckNote, p.textCheckText = looksLikeReview(p)
# ---------------------

def looksLikeReview(paper):
    """ Return (Boolean, Note (str))
	True if the paper appears to be a review paper based on words in the
	extractedText.
	Note is some text explaining Boolean value.

	The algorithm:
	1) convert title, abstract, and a chunk at the beginning of the
	    extracted text into lists of words
	    (lower case, a "word" is text separated by white space)
	2) take the last n words of the abstract, search for them in
	    extracted text words.
	3) if found, search for "review" (or "mini-review") in the words
	    before the end of abstract (actually, search a few words after the
	    abstract too, in case "review" comes shortly after)
	4) if found, call it a review, if not, don't
	5) include a "note" string so we can diagnose problems/findings
    """
    ABSTRACT_WORDS_TO_MATCH = 5	# num words at end of abstract to look for
    				#  when trying to find the end of the abstract
    EXTRA_WORDS  = 2000		# num extra words from extracted text to
				#  consider when searching for eoabstract.
				#  We search up to
				#  len(title)+len(abstract)+EXTRA_WORDS
    WORDS_BEYOND_ABSTRACT = 10	# After finding eoabstract in extracted text,
    				#  add this many words from the eoabstract
				#  when searching for "review"

		    # words in text that make us think it is a review
    reviewWords = [ 'review', 'minireview', 'mini-review']

    pmid	= paper.getSampleName()

    # (1) Get lists of lowercase words from title, abstract, extracted text
    title       = paper.getTitle().lower()
    abstract    = paper.getAbstract().lower()
    extText     = paper.getExtractedText()

    titleWords      = title.split()
    abstractWords   = abstract.split()
    numExtTextWords = len(titleWords) + len(abstractWords) + EXTRA_WORDS

		# [:-1] to remove str that is bulk of text after the split words
    extTextSplit =  extText.split(None, numExtTextWords)[:-1]
    extTextWords =  map( string.lower, extTextSplit)

		# words to search for to find end of abstract
    endAbstractWords = abstractWords[-ABSTRACT_WORDS_TO_MATCH:]

    # (2) If we find the sequence of endAbstractWordsin extTextWords,
    #     set iEndAbstract to idx in extTextWords of 1st endAbstractWord
    iEndAbstract = sublistFind(extTextWords, endAbstractWords)

    if iEndAbstract == -1:	# didn't find words from end of abstract
	return False, 'did not find end of abstract', ''

    # (3) Found end of abstract,
    # add a few words from end of abstract to include in search for "review"
    iLastExtTextWord = iEndAbstract + ABSTRACT_WORDS_TO_MATCH

    # (4) See if we find one of the "review" words
    for revword in reviewWords:
	iReview = sublistFind(extTextWords, [revword], 0, iLastExtTextWord)
	if iReview != -1: break		# found a review word

    # (5) prepare return values
    if iReview == -1:
	isReview = False
	reason = 'review word not found in 1st %d' % iLastExtTextWord
	surroundingText = ''
    else:			# review word found
	if isReviewException(extTextWords, iReview, revword):
	    isReview = False
	    reason = "review word exception"
	else:			# no exception
	    isReview = True
	    reason = "%s found at %d" % (revword, iReview)

	# capture words surrounding the revword
	if iReview == 0:
	    prev1 = '-'		# no prev word to revword
	    prev2 = '-'		# no prev prev word to revword
	elif iReview == 1:
	    prev1 = extTextWords[1]
	    prev2 = '-'		# no prev prev word to revord
	else:			# have at least 2 previous words
	    prev1 = extTextWords[iReview -1]
	    prev2 = extTextWords[iReview -2]
	surroundingText = "%s %s %s %s" % (prev2, prev1, revword,
						extTextWords[iReview+1])
#	if revword == "review" and iReview > 0 \
#		and extTextWords[iReview -1] == 'for':
#	    reason = "for review at %d" % iReview
#	else:
    return isReview, reason, surroundingText
# ---------------------

def isReviewException( extTextWords, iReview, revword):
    """
    Return True if the text around extTextWords[iReview] are an exception
    To the 'revword' and should NOT be treated as text that indicates a
    review article
    """

    exceptionPrevWords = ['for', '(for', 'merit', '(merit', 'peer',
							    'institutional']
    if iReview > 0 and extTextWords[iReview -1] in exceptionPrevWords:
	return True		# FOUND EXCEPTION

    elif iReview > 1 \
	and extTextWords[iReview -2] == 'typesetting,' \
	and extTextWords[iReview -1] == 'and':	# have 2 previous words
	return True		# FOUND EXCEPTION

    elif extTextWords[iReview +1].startswith('board'):
	return True		# FOUND EXCEPTION
    
    return False
# ---------------------

def outputResults( papers,
		):
    """
    """
    SEP = '|'
    sys.stdout.write( SEP.join( [ \
	'PMID',
	'MGI review',
	'Pubmed Review',
	'Text check Review',
	'Note',
	'Surrounding Text',
	'Journal',
	] ) + '\n' )

    for p in papers:
	sys.stdout.write( SEP.join( [ \
		    str(p.pubmedID),
		    str(p.mgiReview),
		    str(p.pubmedReview),
		    str(p.textCheckReview),
		    str(p.textCheckNote),
		    str(p.textCheckText),
		    p.journal,
		    ] ) + '\n' )
    # Summary report
    pmNotMgi   = 0
    textNotMgi = 0
    textAndMgi = 0
    textAndPm  = 0
    for p in papers:		# counters
	if not p.mgiReview     and p.pubmedReview:    pmNotMgi   += 1
	if not p.mgiReview     and p.textCheckReview: textNotMgi += 1
	if     p.mgiReview     and p.textCheckReview: textAndMgi += 1
	if     p.pubmedReview  and p.textCheckReview: textAndPm  += 1

    for fp in [sys.stderr, ]:
	fp.write("\nPapers examined: %d\n" % len(papers))
	fp.write("Marked  review in pubmed but not MGI: %d\n" % pmNotMgi )
	fp.write("Appears review via text but not MGI: %d\n" % textNotMgi )
	fp.write("Appears review via text AND in MGI: %d\n" % textAndMgi )
	fp.write("Appears review via text AND in pubmed: %d\n" % textAndPm )

# ---------------------

def verbose(text):
    if args.verbose: sys.stderr.write(text)
# ---------------------

if __name__ == "__main__":
    main()
