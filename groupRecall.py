#!/usr/bin/env python2.7 
#
# Compute individual curation group precision & recall values for a given
#  file of curation statuses and a given file of predictions.
#
# Output to stdout.
#
import sys
import string
import os
import time
import argparse
import random

DEFAULT_STATUS_FILE     = 'refStatuses.txt'
DEFAULT_PREDICTION_FILE = '_test_pred.txt'
PREDFILE_RECORDSEP = '\n'

#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='Compute recall value for each curation group. Write to stdout')

    parser.add_argument('statusFile', help='file of paper curation statuses')
    parser.add_argument('predictionFile', help='file of paper predictions')

    parser.add_argument('-l', '--long', dest='longOutput', action='store_true',
	required=False,
	help="long output. Write each prediction + paper statuses")

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
	required=False, help="skip helpful messages to stderr")

    parser.add_argument('--test', dest='dotests', action='store_true',
	required=False, help="run informal tests and quit, other args ignored")

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
	self.classification,
	self.ap_status,
	self.gxd_status,
	self.go_status,
	self.tumor_status,
	self.qtl_status,) = record.split(FIELDSEP)

#----------------------

class Prediction (object):
    """
    Is a prediction for a given paper
    Does: knows how to initialize itself from a line from a prediction file
    """
    FIELDSEP = '\t'		# standard for prediction files
    def __init__(self, record):
	(self.pubmed,
	self.trueClass,
	self.predClass,
	self.fpFn,
	self.confidence,
	self.absValue,) = record.split(self.FIELDSEP)
#----------------------

class CurationGroup (object):
    """ IS a curation group, e.g, AP, GO, ...
	HAS simple counts of the number of papers selected for the group, etc.
	DOES check if a paper has been selected for the curation group, 
	    keep track of the number of papers selected, ...
    """
    def __init__(self, statusFieldName):
	"""
	    statusFieldName is sort of the name of this curation group,
	    But we assume it matches status field name in a Paper object.
	    So statusFieldName = 'ap_status' or 'gxd_status' ...
	"""
	self.statusFieldName = statusFieldName
	self.numTP = 0		# num positives for this group = numTP + numFP
	self.numFP = 0
	self.numTN = 0		# num negatives for this group = numTN + numFN
	self.numFN = 0
    #----------------------

    def isGroupPositive(self, paper):
	""" Return true if this paper is known to be selected for this group
	"""
	status = paper.__getattribute__(self.statusFieldName)
#	if status in ['chosen', 'indexed', 'full-coded'] \
#	    and paper.classification != 'discard':         return True
	if status in ['chosen', 'indexed', 'full-coded']:  return True
	else: return False
    #----------------------

    def isGroupNegative(self, paper):
	""" Return true if this paper is known to not be selected for this group
	    Note that a paper can be neither GroupPositive nor GroupNegative
	"""
	status = paper.__getattribute__(self.statusFieldName)
	if paper.classification == 'discard' or status == 'rejected':
	    return True
	else: return False
    #----------------------

    def decideGroupPosNeg(self, paper, pred):
	""" Determine if this paper is a TP, FP, TN, FN or none of these
		for this group.
	    Return one of "TP", "FP", "TN", "FN" or "  "
	    Also increment the correct count for this group.
	"""
	retVal = "  "		# assume it is none for this group
	if self.isGroupPositive(paper):
	    if pred.predClass == "keep":
		retVal = "TP"
		self.numTP += 1
	    else:
		retVal = "FN"
		self.numFN += 1
	elif self.isGroupNegative(paper):
	    if pred.predClass == "discard":
		retVal = "TN"
		self.numTN += 1
	    else:
		retVal = "FP"
		self.numFP += 1
	return retVal
    #----------------------

    def getName(self):		return self.statusFieldName
    def getNumTP(self):		return self.numTP
    def getNumFP(self):		return self.numFP
    def getNumTN(self):		return self.numTN
    def getNumFN(self):		return self.numFN
    def getNumPositive(self):	return self.getNumTP() + self.getNumFN()
    def getNumNegative(self):	return self.getNumTN() + self.getNumFP()

    def getNumSupport(self):
	""" number of papers that are either pos or neg for this group"""
	return self.getNumPositive() + self.getNumNegative()

    def getPrecision(self):
	return float(self.numTP) / float(self.numTP + self.numFP)

    def getRecall(self):
	return float(self.numTP) / float(self.numTP + self.numFN)

#-end CurationGroup ---------------------

def getPapers(papersFile):
    """ Read the file of papers and their curation statuses.
	Return dict {pubmed: Paper object, ...}
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

    curationGroups = [
			CurationGroup('ap_status'),
			CurationGroup('gxd_status'),
			CurationGroup('go_status'),
			CurationGroup('tumor_status'),
			CurationGroup('qtl_status'),
		    ]
    papers = getPapers(args.statusFile)

#    totTruePositives = 0
#    totPredPositives = 0

    predLines = open(args.predictionFile,'r').read().split(PREDFILE_RECORDSEP)
    del predLines[0]			# header line
    del predLines[-1]			# empty line at end after split()

    if args.longOutput: outputLongHeader()

    for predLine in predLines:
	pred = Prediction(predLine)
	paper = papers[pred.pubmed]

#	if paper.classification == 'keep':	# have a true positive
#	    totTruePositives += 1
#	    if pred.predClass == 'keep':	# have a pred positive
#		totPredPositives += 1

	posNegs = []			# TP/FP/TN/FN for each cur group
	for cg in curationGroups:
	    posNegs.append(cg.decideGroupPosNeg(paper, pred))

	if args.longOutput: outputLong(paper, pred, posNegs)


    print "Curation Groups Summary"
    print'%-14s %5s %5s %5s %5s %5s %5s %5s %5s %5s' % \
	("Group",
	"#Pos",
	"#Neg",
	"#Supp",
	"TP",
	"FP",
	"TN",
	"FN",
	"Prec",
	"Recall",
	)
    for cg in curationGroups:
	print'%-14s %5d %5d %5d %5d %5d %5d %5d %5.3f %5.3f' % \
	    (cg.getName(),
	    cg.getNumPositive(),
	    cg.getNumNegative(),
	    cg.getNumSupport(),
	    cg.getNumTP(),
	    cg.getNumFP(),
	    cg.getNumTN(),
	    cg.getNumFN(),
	    cg.getPrecision(),
	    cg.getRecall(),
	    )

#    print '%-14s selected papers: %5d predicted keep: %5d recall: %5.3f' % \
#		('Totals', totTruePositives, totPredPositives,
#				float(totPredPositives)/totTruePositives)
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
		'ap_FP/FN',
		'gxd_status',
		'gxd_FP/FN',
		'go_status',
		'go_FP/FN',
		'tumor_status',
		'tumor_FP/FN',
		'qtl_status',
		'qtl_FP/FN',
		] ) + PREDFILE_RECORDSEP )
# ---------------------

def outputLong( paper,		# Paper record
		pred,		# Prediction record w/ same pubmed as paper
		posNegs,	# one "TP/FP/..." per each group, in order
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
		pred.confidence,
		pred.absValue,
		paper.ap_status,
		posNegs[0],
		paper.gxd_status,
		posNegs[1],
		paper.go_status,
		posNegs[2],
		paper.tumor_status,
		posNegs[3],
		paper.qtl_status,
		posNegs[4],
		] ) + PREDFILE_RECORDSEP )
# ---------------------

def verbose(text):
    if args.verbose: sys.stderr.write(text)
# ---------------------

def runTests():		# some adhoc tests
    g = CurationGroup('ap_status')
    pred1 = Prediction("1234	discard	keep	TN	0.1	0.1")

    paper1 = Paper("1234|keep|routed|gxd|go|tumor|qtl")
    print "groupPositive: " + str(g.isGroupPositive(paper1))
    print "groupNegative: " + str(g.isGroupNegative(paper1))
    print "Prediction: %s\tPosNeg: '%s'\n" % (pred1.predClass, g.decideGroupPosNeg(paper1, pred1))

    paper1 = Paper("1234|discard|routed|gxd|go|tumor|qtl")
    print "groupPositive: " + str(g.isGroupPositive(paper1))
    print "groupNegative: " + str(g.isGroupNegative(paper1))
    print "Prediction: %s\tPosNeg: '%s'\n" % (pred1.predClass, g.decideGroupPosNeg(paper1, pred1))

    paper1 = Paper("1234|discard|chosen|gxd|go|tumor|qtl")
    print "groupPositive: " + str(g.isGroupPositive(paper1))
    print "groupNegative: " + str(g.isGroupNegative(paper1))
    print "Prediction: %s\tPosNeg: '%s'\n" % (pred1.predClass, g.decideGroupPosNeg(paper1, pred1))

    paper1 = Paper("1234|keep|rejected|gxd|go|tumor|qtl")
    print "groupPositive: " + str(g.isGroupPositive(paper1))
    print "groupNegative: " + str(g.isGroupNegative(paper1))
    print "Prediction: %s\tPosNeg: '%s'\n" % (pred1.predClass, g.decideGroupPosNeg(paper1, pred1))

    paper1 = Paper("1234|keep|full-coded|gxd|go|tumor|qtl")
    print "groupPositive: " + str(g.isGroupPositive(paper1))
    print "groupNegative: " + str(g.isGroupNegative(paper1))
    print "Prediction: %s\tPosNeg: '%s'\n" % (pred1.predClass, g.decideGroupPosNeg(paper1, pred1))

    print "TP: %d" % g.getNumTP()
    print "FP: %d" % g.getNumFP()
    print "TN: %d" % g.getNumTN()
    print "FN: %d" % g.getNumFN()
    print

    print "numPos: %d" % g.getNumPositive()
    print "numNeg: %d" % g.getNumNegative()
    print "numSupport: %d" % g.getNumSupport()
    print

    print "Precision: %f" % g.getPrecision()
    print "Recall: %f" % g.getRecall()


if __name__ == "__main__":
    if sys.argv > 0 and sys.argv[1] == "--test": runTests()
    else: main()

