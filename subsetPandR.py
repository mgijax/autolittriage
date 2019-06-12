#!/usr/bin/env python2.7 
#
# Compute recall and precision for subsets of papers
# Current subsets supported:
#  by curation group
#  by journal
#
# Inputs: file of paper info including journal and curation group statuses
#	  a file of paper predictions
#
# Output to stdout.
#
import sys
import string
import os
import time
import argparse

PREDFILE_RECORDSEP = '\n'

#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='Compute precision & recall for subsets of papers. Write to stdout')

    parser.add_argument('paperFile',help='file of paper curation statuses/info')
    parser.add_argument('predictionFile', help='file of paper predictions')

    parser.add_argument('--journal', dest='subsetType', action='store_const',
	const='journal', default='group', help="do analysis by journal")

    parser.add_argument('--group', dest='subsetType', action='store_const',
	const='group', help="do analysis by curation group. Default")

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

#----------------------
class Paper (object):
    """
    Is a paper with curation statuses.
    Does: knows how to initialize itself from a line in a file with statuses
	    for the paper.
    """
    def __init__(self, record):
	FIELDSEP = '|'		# should really get this from sampleDataLib
	(self.pubmed,
	self.trueClass,
	self.ap,
	self.gxd,
	self.go,
	self.tumor,
	self.qtl,
	self.journal) = record.split(FIELDSEP)

#----------------------

class Prediction (object):
    """
    Is:   a prediction for a given paper
    Does: knows how to initialize itself from a line from a prediction file
    """
    FIELDSEP = '\t'		# standard for prediction files
    def __init__(self, record):
	components = record.split(self.FIELDSEP)
	(self.pubmed,
	self.trueClass,
	self.predClass,
	self.fpFn,
	) = components[:4]
	if len(components) == 6:   # if predictions have a confidence & abs val
	    (self.confidence,
	    self.absValue,) = components[4:]
	else:			# just dummy values
	    self.confidence = 0
	    self.absValue   = 0

#----------------------

class SubsetOfPapers (object):
    """ IS:   Information about a subset of papers
	HAS:  Counts of papers in subset, TP, FN, FP, TN
	DOES: Decide if a paper belongs to this subset, 
	      Compute Precision/Recall/NPV for this subset of papers
    """
    def __init__(self, subsetName):
	""" subsetName = 'ap_status' or 'gxd_status' ..."""
	self.subsetName = subsetName
	self.numInSubset = 0		# n papers in this subset
	self.numTP = 0	# n papers in subset correctly predicted keep
	self.numFN = 0	# n papers in subset incorrectly predicted discard
	self.numFP = 0	# n papers in subset incorrectly predicted keep
	self.numTN = 0	# n papers in subset correctly predicted discard
    # ---------------------

    def isPaperInSubset(self, paper):
	"""
	Abstract method.
	Return true if the paper is in this subset
	"""
	return True
    # ---------------------

    def paperVsPrediction(self, paper, prediction):
	""" Compare paper trueClass to prediction
	"""
	if self.isPaperInSubset(paper):
	    self.numInSubset += 1
	    if paper.trueClass == "keep":
		if prediction.predClass =="keep":
		    self.numTP += 1
		else:
		    self.numFN += 1
	    else:			# really a discard
		if prediction.predClass =="keep":
		    self.numFP += 1
		else:
		    self.numTN += 1
    # ---------------------

    def getSubsetName(self):	return self.subsetName
    def getNumInSubset(self):	return self.numInSubset
    def getTP(self):		return self.numTP
    def getFN(self):		return self.numFN
    def getFP(self):		return self.numFP
    def getTN(self):		return self.numTN

    def getRecall(self):
	denom = self.numTP + self.numFN
	if denom == 0: return 0
	else: return float(self.numTP)/float(denom)

    def getPrecision(self):
	denom = self.numTP + self.numFP
	if denom == 0: return 0
	else: return float(self.numTP)/float(denom)

    def getNPV(self):
	# negative predictive value, like precision but for negatives
	denom = self.numTN + self.numFN
	if denom == 0: return 0
	else: return float(self.numTN)/float(denom)

#----------------------

class CurationGroup (SubsetOfPapers):
    """ IS:   A SubsetOfPapers selected by a curation group, e.g, AP, GO, ...
	NOTE: Looking at recall for papers selected by an individual curation
		group makes sense: how many papers actually selected are predicted
		keep.
	      But any paper selected by the group is inherently a "keep", so
		we don't see any true discards *in* a curation group.
	      So within the group, precision = 1 and NPV = 0: not useful
    """
    def isPaperInSubset(self, paper):
	status = paper.__getattribute__(self.subsetName)
	return status in ['chosen', 'indexed', 'full-coded']
#----------------------

class JournalGroup (SubsetOfPapers):
    """ IS:   A SubsetOfPapers from a given journal
    """
    def isPaperInSubset(self, paper):
	return paper.journal == self.subsetName
#----------------------

def getPapers(papersFile):
    """ Read the file of papers and their curation statuses.
	Return {pubmed: Paper object, ...}
    """
    RECORDSEP = '\n'
    rcds = open(papersFile,'r').read().split(RECORDSEP)	# read/split all rcds
    del rcds[0] 			# header line
    del rcds[-1]			# empty line at end after split()
    papers = {}				# {pubmed : Paper object}
    for rcd in rcds:
	paper = Paper(rcd.strip().lower())
	papers[paper.pubmed] = paper

    return papers
#----------------------

#----------------------
# Main prog
#----------------------
def main():

    #### define all the subsets of papers to track
    allPapers = SubsetOfPapers("Totals")

    curationGroups = [  CurationGroup('ap'),
			CurationGroup('gxd'),
			CurationGroup('go'),
			CurationGroup('tumor'),
			CurationGroup('qtl'),
		    ]
    journalGroups = {}	# journalGroups[journal name] is a JournalGroup object

    #### get papers' information and start reading the predictions
    papers = getPapers(args.paperFile)

    predLines = open(args.predictionFile,'r').read().split(PREDFILE_RECORDSEP)
    del predLines[0]			# header line
    del predLines[-1]			# empty line at end after split()

    if args.longOutput: outputLongHeader()

    for predLine in predLines:		# for each prediction
	pred = Prediction(predLine)
	paper = papers[pred.pubmed]

	allPapers.paperVsPrediction(paper, pred)

	for cg in curationGroups:
	    cg.paperVsPrediction(paper, pred)

	doJournalGroup(journalGroups, paper, pred)

	if args.longOutput: outputLong(paper, pred)

    #### Print reports
    if args.subsetType == 'journal':
	printJournalGroupReport(journalGroups, allPapers)
    else:
	printCurationGroupReport(curationGroups, allPapers)
# ---------------------

def doJournalGroup(journalGroups, paper, pred):
    """
    Add the paper/pred to the journalGroup of the journal the paper is from
    """
    j = paper.journal

    if journalGroups.has_key(j):
	group = journalGroups[j]
    else:
	group = JournalGroup(j)
	journalGroups[j] = group

    group.paperVsPrediction(paper, pred)
# ---------------------

def printJournalGroupReport(journalGroups, allPapers):
    hdr = '%6s\t%6s\t%6s\t%6s\t%6s\t%5s\t%5s\t%5s\t%s' \
		% ('Papers', 'TP', 'TN', 'FN', 'FP', 'P', 'R', 'NPV', 'journal')
    print hdr

    for jname in sorted(journalGroups.keys()):
	jg = journalGroups[jname]
	print formatSubsetLine(jg)

    print formatSubsetLine(allPapers)
# ---------------------

def formatSubsetLine(subset):
	nPapers = subset.getNumInSubset()
	TP      = subset.getTP()
	TN      = subset.getTN()
	FN      = subset.getFN()
	FP      = subset.getFP()
	p       = subset.getPrecision()
	r       = subset.getRecall()
	npv     = subset.getNPV()
	name    = subset.getSubsetName()

	return '%6d\t%6d\t%6d\t%6d\t%6d\t%5.3f\t%5.3f\t%5.3f\t%s' \
		    % (nPapers, TP, TN, FN, FP, p, r, npv, name)
# ---------------------

def printCurationGroupReport(curationGroups, allPapers):

    print "Recall for papers selected by each curation group. %d papers analyzed" % allPapers.getNumInSubset()

    for cg in curationGroups:
	truePositives = cg.getNumInSubset()
	predPositives = cg.getTP()
	print '%-14s selected papers: %5d predicted keep: %5d recall: %5.3f' % \
	    (cg.getSubsetName(), truePositives, predPositives, cg.getRecall())

    #### Totals
    tp = allPapers.getTP()
    fn = allPapers.getFN()
    print '%-14s keep     papers: %5d predicted keep: %5d recall: %5.3f' % \
		(allPapers.getSubsetName(), tp+fn, tp, allPapers.getRecall())
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
		'ap',
		'gxd',
		'go',
		'tumor',
		'qtl',
		'journal',
		] ) + PREDFILE_RECORDSEP )
# ---------------------

def outputLong( paper,		# Paper record
		pred,		# Prediction record w/ same pubmed as paper
		):
    """
    Write a combined prediction record with the curation statuses to for
    each curation group from the paper record.
    """
    args.longOutputFile.write( Prediction.FIELDSEP.join( [ \
		pred.pubmed,
		pred.trueClass,
		pred.predClass,
		pred.fpFn,
		str(pred.confidence),
		str(pred.absValue),
		paper.ap,
		paper.gxd,
		paper.go,
		paper.tumor,
		paper.qtl,
		paper.journal,
		] ) + PREDFILE_RECORDSEP )
# ---------------------

def verbose(text):
    if args.verbose: sys.stderr.write(text)
# ---------------------

if __name__ == "__main__":
    main()
