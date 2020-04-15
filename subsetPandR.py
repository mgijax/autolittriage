#!/usr/bin/env python3
#
# Compute recall and precision for subsets of papers
# Current subsets supported:
#  by curation group
#
# Inputs: prediction file that includes "extra info" (see sampleDataLib.py)
#	   that has curation group statuses for the paper being predicted
#
# Output to stdout.
#
import sys
import string
import os
import time
import argparse

PREDFILE_RECORDSEP = '\n'
PREDFILE_FIELDSEP = '|'

NoteToSelf = \
"""
future thought:
* it would not be hard to add cmd line option
    --attr name : would give P, R, NPV for groups defined by diff values for the
        named attr.
        This could work for attrs that are enumerations like journal,
        ap_status, gxd_status, ..., supp data status, isreview, ...
        This would not work well for attr that are counts or that require logic
        to combine different values
    This would be a generalization of the --journal option originally
    implemented here.

    still need to keep
    --group : since this involves logic using curation group statuses,
        it is special and would not work as --attr

* to do --attr, will need
    a subclass of SubsetOfPapers, something like "PapersByAttr".
    Takes name of extra info field to use & individual value - there would be 1
    instance per value in the field

    change report formatting for --attr
"""
#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='Compute precision & recall for curation groups. Write to stdout')

    parser.add_argument('predictionFile', help='file of paper predictions')

    parser.add_argument('--group', dest='subsetType', action='store_const',
    	const='group', default='group',
        help="do analysis by curation group. Default")

# July 24, 2019: not dealing with journal analysis for now.
#    parser.add_argument('--journal', dest='subsetType', action='store_const',
#  	const='journal', default='group', help="do analysis by journal")

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

class Prediction (object):
    """
    Is:   a prediction for a given paper
    Does: knows how to initialize itself from a line from a prediction file
    """
    def __init__(self, record):
        # basic prediction fields
        components = record.lower().split(PREDFILE_FIELDSEP)
        (self.pubmed,
        self.predClass,
        self.confidence,
        self.absValue,
        self.trueClass,
        self.fpFn,
        # extra info fields, hard coded. Yuck.
        # Needs to match ClassifiedSample extra info fields
        self.creationDate,
        self.year,
        self.isReview,
        self.refType,
        self.suppStatus,
        self.ap,
        self.gxd,
        self.go,
        self.tumor,
        self.qtl,
        self.journal,
        self.abstractLen,
        self.textLen,
        ) = components
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
        Return true if the paper is in this subset
        This is likely the method that needs to be overridden for a Subset.
        """
        return True
    # ---------------------

    def truthVsPrediction(self, prediction):
        """ Compare paper trueClass to prediction
        """
        if self.isPaperInSubset(prediction):
            self.numInSubset += 1
            if prediction.trueClass == "keep":
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
                group makes sense: how many papers actually selected are
                predicted keep.
              But any paper selected by the group is inherently a "keep", so
                we don't see any true discards *in* a curation group.
              So within the group, precision = 1 and NPV = 0: not useful
    """
    def isPaperInSubset(self, prediction):
        status = prediction.__getattribute__(self.subsetName)
        return status in ['chosen', 'indexed', 'full-coded']
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
    # not supporting this for now
#    journalGroups = {}	# journalGroups[journal name] is a JournalGroup object

    predLines = open(args.predictionFile,'r').read().split(PREDFILE_RECORDSEP)
    del predLines[0]			# header line
    del predLines[-1]			# empty line at end after split()

    if args.longOutput: outputLongHeader()

    for predLine in predLines:		# for each prediction
        pred = Prediction(predLine)

        allPapers.truthVsPrediction(pred)

        for cg in curationGroups:
            cg.truthVsPrediction(pred)

#	doJournalGroup(journalGroups, pred)

        if args.longOutput: outputLong(pred)

    #### Print reports
    printCurationGroupReport(curationGroups, allPapers)
# ---------------------

def doJournalGroup(journalGroups, pred):
    """
    NOT SUPPORTING this for now.
    Add the pred to the journalGroup of the journal the paper is from
    """
    j = pred.journal

    if j in journalGroups:
        group = journalGroups[j]
    else:
        group = JournalGroup(j)
        journalGroups[j] = group

    group.truthVsPrediction(pred)
# ---------------------

def printJournalGroupReport(journalGroups, allPapers):
    # NOT SUPPORTING this for now.
    hdr = '%6s\t%6s\t%6s\t%6s\t%6s\t%5s\t%5s\t%5s\t%s' \
                % ('Papers', 'TP', 'TN', 'FN', 'FP', 'P', 'R', 'NPV', 'journal')
    print(hdr)

    for jname in sorted(journalGroups.keys()):
        jg = journalGroups[jname]
        print(formatSubsetLine(jg))

    print(formatSubsetLine(allPapers))
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

    print("Recall for papers selected by each curation group. %d papers analyzed" % allPapers.getNumInSubset())

    for cg in curationGroups:
        truePositives = cg.getNumInSubset()
        predPositives = cg.getTP()
        print('%-14s selected papers: %5d predicted keep: %5d recall: %5.3f' % \
            (cg.getSubsetName(), truePositives, predPositives, cg.getRecall()))

    #### Totals
    tp = allPapers.getTP()
    fn = allPapers.getFN()
    print('%-14s keep     papers: %5d predicted keep: %5d recall: %5.3f' % \
                (allPapers.getSubsetName(), tp+fn, tp, allPapers.getRecall()))
    print("Predictions from %s - %s" % (args.predictionFile, time.ctime()))
# ---------------------

def outputLongHeader():
    """
    Write header line for long output file
    """
    args.longOutputFile.write( PREDFILE_FIELDSEP.join( [ \
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

def outputLong( pred,		# Prediction record w/ same pubmed as paper
                ):
    """
    Write a combined prediction record with the curation statuses to for
    each curation group from the paper record.
    """
    args.longOutputFile.write( PREDFILE_FIELDSEP.join( [ \
                pred.pubmed,
                pred.trueClass,
                pred.predClass,
                pred.fpFn,
                str(pred.confidence),
                str(pred.absValue),
                pred.ap,
                pred.gxd,
                pred.go,
                pred.tumor,
                pred.qtl,
                pred.journal,
                ] ) + PREDFILE_RECORDSEP )
# ---------------------

def verbose(text):
    if args.verbose:
        sys.stderr.write(text)
        sys.stderr.flush()
# ---------------------

if __name__ == "__main__":
    main()
