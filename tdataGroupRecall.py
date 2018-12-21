#!/usr/bin/env python2.7 
#
# Compute individual curation group recall values for a given
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

DEFAULT_STATUS_FILE     = 'docStatuses.txt'
DEFAULT_PREDICTION_FILE = 'SGDlog_test.out'
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
	""" statusFieldName = 'ap_status' or 'gxd_status' ..."""
	self.statusFieldName = statusFieldName
	self.numSelected = 0		# number of papers that are selected
					#  for this curation group
	self.numPredPositives = 0	# number of papers selected for this
					#  group that are predicted as keepers 
    def selectedVsPredicted(self, paper, prediction):
	status = paper.__getattribute__(self.statusFieldName)
	if status in ['chosen', 'indexed', 'full-coded']:
	    self.numSelected += 1
	    if prediction.predClass == "keep":
		self.numPredPositives += 1

    def getNumSelected(self):	return self.numSelected
    def getNumPredPositives(self):	return self.numPredPositives
    def getName(self):		return self.statusFieldName
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

    curationGroups = [
			CurationGroup('ap_status'),
			CurationGroup('gxd_status'),
			CurationGroup('go_status'),
			CurationGroup('tumor_status'),
			CurationGroup('qtl_status'),
		    ]
    papers = getPapers(args.statusFile)

    totTruePositives = 0
    totPredPositives = 0

    predLines = open(args.predictionFile,'r').read().split(PREDFILE_RECORDSEP)
    del predLines[0]			# header line
    del predLines[-1]			# empty line at end after split()

    if args.longOutput: outputLongHeader()

    for predLine in predLines:
	pred = Prediction(predLine)
	paper = papers[pred.pubmed]

	if args.longOutput: outputLong(paper, pred)

	if paper.classification == 'keep':	# have a true positive
	    totTruePositives += 1
	    if pred.predClass == 'keep':	# have a pred positive
		totPredPositives += 1

	for cg in curationGroups:
	    cg.selectedVsPredicted(paper, pred)

    print "Recall for papers selected by each curation group"
    for cg in curationGroups:
	predPositives = cg.getNumPredPositives()
	truePositives = cg.getNumSelected()
	print '%-14s selected papers: %5d predicted keep: %5d recall: %5.3f' % \
		    (cg.getName(), truePositives, predPositives,
				    float(predPositives)/truePositives)

    print '%-14s selected papers: %5d predicted keep: %5d recall: %5.3f' % \
		('Totals', totTruePositives, totPredPositives,
				float(totPredPositives)/totTruePositives)
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
		pred.confidence,
		pred.absValue,
		paper.ap_status,
		paper.gxd_status,
		paper.go_status,
		paper.tumor_status,
		paper.qtl_status,
		] ) + PREDFILE_RECORDSEP )
# ---------------------

def verbose(text):
    if args.verbose: sys.stderr.write(text)
# ---------------------

if __name__ == "__main__":
    main()
