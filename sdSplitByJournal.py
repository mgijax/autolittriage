#!/usr/bin/env python2.7 
#
# sdSplitByJournal.py
# Takes one or more files of samples and randomly splits the samples into 2 outputs
#   1) the "selected" samples
#      - the selected samples can be restricted to only MGI monitored journals or
#        unrestricted and selected from any journals in the input sample sets
#   2) "leftovers" the rest of the samples
#
#   (1) written to a file specified on command line
#   (2) written to a file specified on command line
#   a Summary report is written to stdout
#
# ClassifiedSampleRecord Class in sampleDataLib.py is responsible for the sample
#   handling
#
# Assumes all input files have the same column structure. see sampleDataLib.py.
#
# At the moment this does NOT consider/preserve the distribution of keep/discard
# for each journal. We should probably add that.
#
import sys
import string
import os
import time
import argparse
import random
# extend path up multiple parent dirs, hoping we can import sampleDataLib
sys.path = ['/'.join(dots) for dots in [['..']*i for i in range(1,4)]] + \
		sys.path
import sampleDataLib

DEFAULT_OUTPUT_SELECTED = 'selectedRefs.txt'
DEFAULT_OUTPUT_LEFTOVER = 'leftoverRefs.txt'

DEFAULT_MGI_JOURNALS_FILE = 'mgiJournals.all.txt'
#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='journal by journal select random samples. Summary stats to stdout')

    parser.add_argument('inputFiles', nargs=argparse.REMAINDER,
    	help='files of samples')

    parser.add_argument('-f', '--fraction', dest='fraction', action='store',
        required=True, type=float, default=0.2,
        help='fraction of articles from each journal to select. Float 0..1 .')

    parser.add_argument('--selectedfile', dest='selectedFile', action='store',
	required=False, default=DEFAULT_OUTPUT_SELECTED,
    	help='where to write articles randomly selected from monitored '+
	'journals. Default: ' + DEFAULT_OUTPUT_SELECTED)

    parser.add_argument('--leftoverfile', dest='leftoverFile', action='store',
	required=False, default=DEFAULT_OUTPUT_LEFTOVER,
    	help='where to write leftover articles not selected'+
	'. Default: ' + DEFAULT_OUTPUT_LEFTOVER)

    parser.add_argument('--mgijournals', dest='mgiJournalsFile', action='store',
	required=False, default=DEFAULT_MGI_JOURNALS_FILE,
    	help='file containing the list of MGI journals. Default: '
						+ DEFAULT_MGI_JOURNALS_FILE)

    parser.add_argument('--alljournals', dest='allJournals', action='store_true',
	required=False, help="include all journals, not just MGI monitored")

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
	required=False, help="skip helpful messages to stderr")

    args = parser.parse_args()

    return args
#----------------------

args = parseCmdLine()

#----------------------

def getMgiJournals(mgiJournalsFile):
    """ return list of MGI monitored journalNames
    """
    journals = []
    fp = open(mgiJournalsFile, 'r')
    for j in fp:
	journals.append( cleanJournalName(j) )
    fp.close()
    return journals
#----------------------

def cleanJournalName(s):
    j = s.strip().lower()
    jn = '_'.join(j.split(' ')).strip()
    return jn
#----------------------

class JournalCollection (object):
    """
    # IS a collection of journals, each with its list of samples/articles
    """
    def __init__(self):
	self.journals = {}		# { journalName: [ list of Samples ] }
	self.numSelectedByJournal = {}	# { journalName: num selected samples }
	self.totNumSamples = 0
    #----------------------

    def addSample(self, journalName,
	sample,			# ClassifiedSample
	):
	self.journals.setdefault(journalName, []).append(sample)
	self.numSelectedByJournal[journalName] = 0
	self.totNumSamples += 1
    #----------------------

    def selectRandomSetFrom(self, journalName, fraction):
	"""
	Return two lists of random samples from the journal,
	    selected and not-selected
	"""
	samples = self.journals[journalName]
	selectedSamples = []
	leftoverSamples = []

	for sample in samples:
	    if random.random() < float(fraction):
		selectedSamples.append(sample)
	    else:
		leftoverSamples.append(sample)

	self.numSelectedByJournal[journalName] = len(selectedSamples)
	return selectedSamples, leftoverSamples
    #----------------------

    def getSamplesFrom(self, journalName):
	return self.journals[journalName]
    def getNumSamplesFrom(self, journalName):
	return len(self.journals[journalName])

    def getNumSamples(self):
	return self.totNumSamples

    def getJournalNames(self):
	return self.journals.keys()
    def getNumJournals(self):
	return len(self.journals.keys())

    def getNumSelectedFrom(self, journalName):
	return self.numSelectedByJournal[journalName]
    def getNumSelected(self,):
	tot = 0
	for n in self.numSelectedByJournal.values():
	    tot += n
	return tot
    def getNumLeftover(self,):
	return self.totNumSamples - self.getNumSelected()
# end class ----------------------

#----------------------
# Main prog
#----------------------

def main():

    verbose("Splitting article set\n")
    startTime = time.time()

    mgiJournalNames = getMgiJournals(args.mgiJournalsFile)

    # the final sample sets
    selectedSampleSet = sampleDataLib.ClassifiedSampleSet()
    leftoverSampleSet = sampleDataLib.ClassifiedSampleSet()

    mgiJournalCollection   = JournalCollection()
    otherJournalCollection = JournalCollection()

    ### Loop through all input files, build JournalCollections
    for fn in args.inputFiles:
	verbose("Reading %s\n" % fn)
	inputSampleSet = sampleDataLib.ClassifiedSampleSet().read(fn)

	for sample in inputSampleSet.sampleIterator():
	    journalName = cleanJournalName( sample.getJournal() )
	    if journalName in mgiJournalNames:
		mgiJournalCollection.addSample(journalName, sample)
	    else:
		otherJournalCollection.addSample(journalName, sample)
	 
    ### Loop through journals. for each, select random fraction of samples,
    for journalName in mgiJournalCollection.getJournalNames():
	selected,leftover = mgiJournalCollection.selectRandomSetFrom(journalName,
								    args.fraction)
	selectedSampleSet.addSamples(selected)
	leftoverSampleSet.addSamples(leftover)

    for journalName in otherJournalCollection.getJournalNames():
	if args.allJournals:
	    selected,leftover = otherJournalCollection.selectRandomSetFrom( \
							journalName, args.fraction)
	    selectedSampleSet.addSamples(selected)
	    leftoverSampleSet.addSamples(leftover)
	else:
	    leftoverSampleSet.addSamples( \
				otherJournalCollection.getSamplesFrom(journalName))

    ### Write output files
    selectedSampleSet.write(args.selectedFile)
    leftoverSampleSet.write(args.leftoverFile)

    ### Write summary report
    numMgiJournalsSeen   = mgiJournalCollection.getNumJournals()
    numOtherJournals     = otherJournalCollection.getNumJournals()

    numMgiSamples         = mgiJournalCollection.getNumSamples()
    numMgiSelectedSamples = mgiJournalCollection.getNumSelected()
    numMgiLeftoverSamples = mgiJournalCollection.getNumLeftover()

    numOtherSamples         = otherJournalCollection.getNumSamples()
    numOtherSelectedSamples = otherJournalCollection.getNumSelected()
    numOtherLeftoverSamples = otherJournalCollection.getNumLeftover()

    print "Selecting random set of articles. Fraction: %5.3f" % args.fraction
    print args.inputFiles
    print time.ctime()
    print
    printSummary("Overall",
	numMgiJournalsSeen + numOtherJournals,
	numMgiSamples + numOtherSamples,
	selectedSampleSet.getNumSamples(),
	leftoverSampleSet.getNumSamples(),
	)
    print
    title = "MGI Journals: %d - all elegible" % len(mgiJournalNames)
    printSummary(title,
	numMgiJournalsSeen,
	numMgiSamples,
	numMgiSelectedSamples,
	numMgiLeftoverSamples,
	)

    if args.allJournals: suffix = " - elegible for selection"
    else: suffix = " - NOT elegible for selection"
    print
    printSummary("Non-MGI Journals" + suffix,
	numOtherJournals,
	numOtherSamples,
	numOtherSelectedSamples,
	numOtherLeftoverSamples,
	)

    ### write details report
    # for each elegible journal:
    cols = ["articles",			# num articles
	    "% of elegible",		# % of all elegible articles
	    "selected",			# num selected
	    "% of selected",		# % of all selected articles
	    "% from journal",		# % of all articles in this journal
	    "journal",
	    ]
    print '\t'.join(cols)

    numElegible = mgiJournalCollection.getNumSamples()
    if args.allJournals: numElegible += otherJournalCollection.getNumSamples()
    
    numSelected = selectedSampleSet.getNumSamples()

    for journalName in sorted(mgiJournalCollection.getJournalNames() + \
					otherJournalCollection.getJournalNames()):
	if journalName in mgiJournalNames:
	    collection = mgiJournalCollection
	else:
	    collection = otherJournalCollection

	numJSamples  = collection.getNumSamplesFrom(journalName)
	numJSelected = collection.getNumSelectedFrom(journalName)

	spaces = ' ' * 3
	print "%5d %s %5.2f%% %s %5d %s %5.2f%% %s %5.2f%% %s %s" % ( \
		    numJSamples, spaces,
		    float(100.0 * float(numJSamples)/numElegible), spaces,
		    numJSelected, spaces,
		    float(100.0 * float(numJSelected)/numSelected), spaces,
		    float(100.0 * float(numJSelected)/numJSamples), spaces,
		    journalName,
		    )

    verbose( "Total time: %8.3f seconds\n\n" % (time.time()-startTime))
# ---------------------

def printSummary(title, numJournals, numArticles, numSelected, numLeftover):
    print title
    print "Journals in the input: \t%d" % numJournals
    print "Total articles: \t%d" % numArticles
    print "Total selected articles: %d  %4.2f%%" % (numSelected,
						float(numSelected)/numArticles)
    print "Total leftover articles: %d  %4.2f%%" % (numLeftover,
						float(numLeftover)/numArticles)
# ---------------------

def verbose(text):
    if args.verbose:
	sys.stderr.write(text)
	sys.stderr.flush()
# ---------------------

if __name__ == "__main__":
    main()
