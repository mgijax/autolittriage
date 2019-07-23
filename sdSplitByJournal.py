#!/usr/bin/env python2.7 
#
# sdSplitByJournal.py
# Takes one or more files of samples and splits the samples into 2 outputs
#   1) random samples only from monitored journals in the same distribution
#       as those journals
#   2) "leftovers" the rest of the samples (non-selected and non-monitored
#        journals)
#   (1) written to a file specified on command line
#   (2) written to a file specified on command line
#   Summary report is written to stdout
#
# SampleRecord Class in sampleDataLib.py is responsible for the sample handling
#
# Assumes all input files have the same column structure. see SampleRecord.
#
# Use this to get a subset of samples with the same journal distribution as
# the input. So for instance, to generate a test set.
#
# NOTE currently this script is only considering articles from the MGI
#  monitored journals. So it is not really the distribution across all journals
# 
# This only works IF the input set already has the distribution we want.
# If the input is some other funky/ill-defined distribution, then we'd need
# to know the fraction of inputs desired for each journal, and we'd need a 
# different script.
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

DEFAULT_OUTPUT_SELECTED = 'selectedRefs.txt'
DEFAULT_OUTPUT_LEFTOVER = 'leftoverRefs.txt'

DEFAULT_MGI_JOURNALS_FILE = 'mgiJournals.all.txt'
#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='split samples into MGI monitored journals vs. not. Write to stdout')

    parser.add_argument('inputFiles', nargs=argparse.REMAINDER,
    	help='files of samples')

    parser.add_argument('-f', '--fraction', dest='fraction', action='store',
        required=True, type=float, default=0.0,
        help='fraction of articles from each journal to select. Float 0..1 .')

    parser.add_argument('--selectedrefs', dest='selectedFile', action='store',
	required=False, default=DEFAULT_OUTPUT_SELECTED,
    	help='where to write articles randomly selected from monitored '+
	'journals. Default: ' + DEFAULT_OUTPUT_SELECTED)

    parser.add_argument('--leftoverrefs', dest='leftoverFile', action='store',
	required=False, default=DEFAULT_OUTPUT_LEFTOVER,
    	help='where to write leftover articles not selected'+
	'. Default: ' + DEFAULT_OUTPUT_LEFTOVER)

    parser.add_argument('--mgijournals', dest='mgiJournalsFile', action='store',
	required=False, default=DEFAULT_MGI_JOURNALS_FILE,
    	help='file containing the list of MGI journals. Default: '
						+ DEFAULT_MGI_JOURNALS_FILE)

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
	required=False, help="skip helpful messages to stderr")

    args = parser.parse_args()

    return args
#----------------------

args = parseCmdLine()

#----------------------
class JournalCounts (object):
    numSelected = 0
    numLeftover = 0

#----------------------
def getMgiJournals(mgiJournalsFile):
    """ return dict of MGI monitored journal names
	{journalname: [], ...}		# list of samples seen in the journal
    """
    journals = {}
    fp = open(mgiJournalsFile, 'r')
    for j in fp:
	j = j.strip().lower()
	jn = '_'.join(j.split(' '))
	journals[jn.strip()] = []
    fp.close()
    return journals
#----------------------
# Main prog
#----------------------
def main():

    verbose("Distributing Articles over MGI monitored Journals\n")
    startTime = time.time()

    # extend path up multiple parent dirs, hoping we can import sampleDataLib
    sys.path = ['/'.join(dots) for dots in [['..']*i for i in range(1,4)]] + \
		    sys.path
    import sampleDataLib

    counts = { 'allSamples': 0, 'fromMonitored':0,}

    mgiJournals = getMgiJournals(args.mgiJournalsFile)

    selectedSampleSet = sampleDataLib.ClassifiedSampleSet()
    leftoverSampleSet = sampleDataLib.ClassifiedSampleSet()

    ### Loop through all input files, reading all sample records.
    ### Samples from monitored journals go to selectedSampleSet
    ### Samples from non-monitored journals go to leftoverSampleSet
    for fn in args.inputFiles:

	verbose("Reading %s\n" % fn)
	inputSampleSet = sampleDataLib.ClassifiedSampleSet().read(fn)

	for rcdnum, sr in enumerate(inputSampleSet.sampleIterator()):
	    counts['allSamples'] += 1
	    journal = sr.getJournal().strip().lower()
	    if mgiJournals.has_key(journal):
		counts['fromMonitored'] += 1
		mgiJournals[journal].append(sr)
	    else:
		leftoverSampleSet.addSample(sr)

    ### NOW, loop through mgiJournals. for each, select random fraction of samples,
    ### add random samples to selectedSampleSet or leftoverSampleSet
    mgiJournalCounts = {}	# mgiJournalCounts[journalname] = num selected
    totNumSelected = 0		# num selected across all MGI journals

    for journalName, samples in mgiJournals.items():
	numInJournal = len(samples)
	numToSelect  = int( (numInJournal * args.fraction) + 0.5)

	# save counts so we can compute/output percentages below
	mgiJournalCounts[journalName] = numToSelect
	totNumSelected += numToSelect

	# random list of sample indexes, in sorted order
	randomIndexes = sorted(random.sample( range(numInJournal), numToSelect))

	# loop through the samples in list order, selecting the ones whose
	#  index is in randomIndexes
	for i in range(numInJournal):
	    if len(randomIndexes) > 0 and i == randomIndexes[0]:
		selectedSampleSet.addSample(samples[i])
		del randomIndexes[0]
	    else:
		leftoverSampleSet.addSample(samples[i])

    # Write output files
    selectedSampleSet.write(args.selectedFile)
    leftoverSampleSet.write(args.leftoverFile)

    ### Write report to stdout
    print "Monitored Journals: \t%d" % len(mgiJournals)
    print "Total articles: \t%d" % counts['allSamples']
    print "From monitored journals: %d" % counts['fromMonitored']
    print "From non-monitored journals: %d" % \
				(counts['allSamples'] - counts['fromMonitored'])
    print "Total selected articles: %d" % totNumSelected
    print "Total leftover articles: %d" % (counts['allSamples'] - totNumSelected)
    print
    # column headings
    print "#articles\t%% of all\t#selected\t%% of sel\tjournal"

    for journalName in sorted(mgiJournals.keys()):
	samples = mgiJournals[journalName]
	numInJournal = len(samples)
	numSelected  = mgiJournalCounts[journalName]

	    # fraction of fromJournal/fromMonitored should be same as 
	    #  numselected/totNumSelected. If not, we've miscalculated somehow.
	print "%d\t%7.4f\t\t%d\t%7.4f\t%s" % ( \
		    numInJournal,
		    float(100.0 * float(numInJournal)/counts['fromMonitored']),
		    numSelected,
		    float(100.0 * float(numSelected)/totNumSelected),
		    journalName
		    )
    verbose( "Total time: %8.3f seconds\n\n" % (time.time()-startTime))
# ---------------------

def verbose(text):
    if args.verbose:
	sys.stderr.write(text)
	sys.stderr.flush()

# ---------------------
if __name__ == "__main__":
    main()
