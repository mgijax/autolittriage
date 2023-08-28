#
# sdSplitSamples.py
# Takes 1 or more files of samples & randomly splits the samples into 2 outputs
#   1) the "retained" samples (some specified fraction of the input samples)
#      - can be restricted to only MGI monitored journals or
#        unrestricted and retained from any journals in the input sample sets
#   2) "leftovers" the rest of the samples
#
#   (1) written to a file specified on command line
#   (2) written to a file specified on command line
#   a Summary report is written to stdout
#
# This simply flips a weighted coin for each reference in the input. It does
#  not try to keep the journal or pos/neg distributions in the retained
#  file consistent with the inputs.
#  (although, by random selection, the distributions will likely be maintained)
#
# ClassifiedRefSampleRecord Class in sampleDataLib.py is responsible for the
#   sample handling
#
# Assumes all input files have the same column structure. see sampleDataLib.py.
#
import sys
import string
import os
import time
import argparse
import random
import sampleDataLib

DEFAULT_OUTPUT_RETAINED = 'retainedRefs.txt'
DEFAULT_OUTPUT_LEFTOVER = 'leftoverRefs.txt'
DEFAULT_MGI_JOURNALS_FILE = 'journalsMonitored.txt'
DEFAULT_SAMPLE_TYPE = 'PrimTriageClassifiedSample'
#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='Randomly split sample files into "retained" set & ' +
                '"leftovers". Summary stats to stdout.')

    parser.add_argument('inputFiles', nargs=argparse.REMAINDER,
    	help='files of samples')

    parser.add_argument('-f', '--fraction', dest='fraction', action='store',
        required=False, type=float, default=0.2,
        help='fraction of articles to be in the retained set. Float 0..1 .')

    parser.add_argument('--retainedfile', dest='retainedFile', action='store',
        required=False, default=DEFAULT_OUTPUT_RETAINED,
    	help='retained output file. Default: ' + DEFAULT_OUTPUT_RETAINED)

    parser.add_argument('--leftoverfile', dest='leftoverFile', action='store',
        required=False, default=DEFAULT_OUTPUT_LEFTOVER,
    	help='leftover output file. Default: ' + DEFAULT_OUTPUT_LEFTOVER)

    parser.add_argument('--mgijournalsfile', dest='mgiJournalsFile',
        action='store', required=False, default=DEFAULT_MGI_JOURNALS_FILE,
    	help='file containing the list of MGI journal names. Default: '
                                                + DEFAULT_MGI_JOURNALS_FILE)

    parser.add_argument('--onlymgi', dest='onlyMgi', action='store_true',
        required=False,
        help="only retain refs from MGI journals. Default: all journals")

    parser.add_argument('--sampletype', dest='sampleObjTypeName',
        default=DEFAULT_SAMPLE_TYPE,
        help="Sample class name to use if not specified in sample file. " + 
                                        "Default: %s" % DEFAULT_SAMPLE_TYPE)

    parser.add_argument('--seed', dest='seed', action='store',
        required=False, type=int, default=int(time.time()),
    	help='int seed for random(). Default: a new seed will be generated')

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    args = parser.parse_args()

    return args
#----------------------

args = parseCmdLine()

#----------------------
def getMgiJournals(mgiJournalsFile):
    """ return Set of MGI monitored journalNames
    """
    journals = set()
    fp = open(mgiJournalsFile, 'r')
    for j in fp:
        journals.add(cleanJournalName(j))
    fp.close()
    return journals
#----------------------
def cleanJournalName(s):
    j = s.strip().lower()
    jn = '_'.join(j.split(' ')).strip()
    return jn
#----------------------

#----------------------
def main():
#----------------------
    startTime = time.time()
    random.seed(args.seed)
    mgiJournalsNames = getMgiJournals(args.mgiJournalsFile)

    retainedSampleSet = None	# the final sample sets
    leftoverSampleSet = None	#   ...

    allJournals = set()		# all journal names seen in input

    sampleObjType = getattr(sampleDataLib, args.sampleObjTypeName)

    for fn in args.inputFiles:
        verbose("Reading %s\n" % fn)
        inputSampleSet = sampleDataLib.ClassifiedRefSampleSet( \
                                        sampleObjType=sampleObjType).read(fn)

        if not retainedSampleSet:	# processing 1st input file
            sampleObjType     = inputSampleSet.getSampleObjType()
            retainedSampleSet = sampleDataLib.ClassifiedRefSampleSet( \
                                                sampleObjType=sampleObjType)
            leftoverSampleSet = sampleDataLib.ClassifiedRefSampleSet( \
                                                sampleObjType=sampleObjType)
            verbose("Sample type: %s\n" % sampleObjType.__name__)
        else:
            if sampleObjType != inputSampleSet.getSampleObjType():
                sys.stderr.write( \
                    "Input files have inconsistent sample types: %s & %s\n" % \
                    (sampleObjType.__name__,
                    inputSampleSet.getSampleObjType().__name__) )
                exit(5)

        allJournals |= inputSampleSet.getJournals()

        for sample in inputSampleSet.sampleIterator():
            if args.onlyMgi and not cleanJournalName(sample.getJournal()) \
                                                        in mgiJournalsNames:
                retain = False
            else:
                retain = random.random() < float(args.fraction)

            if retain:
                retainedSampleSet.addSample(sample)
            else:
                leftoverSampleSet.addSample(sample)
    ### Write output files
    retainedSampleSet.write(args.retainedFile)
    leftoverSampleSet.write(args.leftoverFile)

    ### Write summary report
    summary = "\nSummary:  "
    summary += "Retaining random set of articles. Fraction: %5.3f\n" \
                                                            % args.fraction
    summary += time.ctime() + '\n'
    summary += "Seed:  %d\n" % args.seed
    if args.onlyMgi:
        summary += "Only samples from MGI monitored journals are eligible\n"
    else:
        summary += "Samples from any journal are eligible\n"
    summary += str(args.inputFiles) + '\n'

    summary += "Input Totals:\n"
    totRefs = retainedSampleSet.getNumSamples() + \
                                            leftoverSampleSet.getNumSamples()
    totPos  = retainedSampleSet.getNumPositives() + \
                                            leftoverSampleSet.getNumPositives()
    totNeg  = retainedSampleSet.getNumNegatives() + \
                                            leftoverSampleSet.getNumNegatives()
    summary += formatSummary(totRefs, totPos, totNeg, len(allJournals))
    summary += '\n'

    summary += "Retained Set Totals:\n"
    summary += formatSummary(retainedSampleSet.getNumSamples(),
                            retainedSampleSet.getNumPositives(),
                            retainedSampleSet.getNumNegatives(),
                            len(retainedSampleSet.getJournals()),
                            )
    summary += "(%5.3f%% of inputs)\n" %  \
                            (100.0 * retainedSampleSet.getNumSamples()/totRefs)
    summary += '\n'
    summary += "Leftover Set Totals:\n"
    summary += formatSummary(leftoverSampleSet.getNumSamples(),
                            leftoverSampleSet.getNumPositives(),
                            leftoverSampleSet.getNumNegatives(),
                            len(leftoverSampleSet.getJournals()),
                            )
    sys.stdout.write(summary + '\n')
    return
# ---------------------

def formatSummary(numRefs, numPos, numNeg, numJournals):

    sum = "%d refs: %d positive (%4.1f%%) %d negative (%4.1f%%) %d Journals\n" \
                    % (numRefs,
                    numPos, (100.0 * numPos/numRefs),
                    numNeg, (100.0 * numNeg/numRefs),
                    numJournals,)
    return sum
# ---------------------

def verbose(text):
    if args.verbose:
        sys.stderr.write(text)
        sys.stderr.flush()
# ---------------------

if __name__ == "__main__":
    main()
