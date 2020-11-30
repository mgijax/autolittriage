#!/usr/bin/env python3
#
# journalDist.py
# Reads sample records from files and computes the journal counts/distribution 
#  across 3 sets:
#   all articles
#   discard articles
#   keep articles
# Write to stdout:
#  journalname all_count, discard_count, keep_count

# ClassifiedSampleSet in sampleDataLib.py is responsible for reading the samples
#   and sample details.
#
import sys
import argparse

# extend path up multiple parent dirs, hoping we can import sampleDataLib
sys.path = ['/'.join(dots) for dots in [['..']*i for i in range(1,8)]] + \
                sys.path
import sampleDataLib

DEFAULT_SAMPLE_TYPE  = "ClassifiedSample"
#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='Report journal counts from files of samples. Write to stdout')

    parser.add_argument('inputFiles', nargs=argparse.REMAINDER,
        help='files of samples, "-" for stdin')

    parser.add_argument('--sampletype', dest='sampleObjTypeName',
        default=DEFAULT_SAMPLE_TYPE,
        help="Sample class name to use if not specified in sample file. " +
                                        "Default: %s" % DEFAULT_SAMPLE_TYPE)

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    return parser.parse_args()
#-----------------------------------


class JournalCounter (object):
    # has totalCount, positive & negative counts
    def __init__(self):
        self.totalCount    = 0
        self.positiveCount = 0
        self.negativeCount = 0

#----------------------
# Main prog
#----------------------
args = parseCmdLine()

def main():

    # get default sampleObjType
    if not hasattr(sampleDataLib, args.sampleObjTypeName):
        sys.stderr.write("invalid sample class name '%s'" \
                                                    % args.sampleObjTypeName)
        exit(5)
    sampleObjType = getattr(sampleDataLib, args.sampleObjTypeName)

    counts = {}		# counts[journal] is a JournalCounter
    nPos   = 0	        # num of positive (e.g., keep) articles seen
    nNeg   = 0	        # num of negative (e.g., discard) articles seen

    firstFile = True

    for fn in args.inputFiles:

        if fn == '-': fn = sys.stdin
        sampleSet = sampleDataLib.ClassifiedSampleSet( \
                                        sampleObjType=sampleObjType).read(fn)
        if firstFile:
            sampleObjType = sampleSet.getSampleObjType()
            verbose("Sample type: %s\n" % sampleObjType.__name__)
            firstFile = False
        else:
            if sampleObjType != sampleSet.getSampleObjType():
                sys.stderr.write( \
                    "Input files have inconsistent sample types: %s & %s\n" % \
                    (sampleObjType.__name__,
                    sampleSet.getSampleObjType().__name__) )
                exit(5)

        for s in sampleSet.getSamples():
            journal = s.getJournal()

            if journal in counts:
                jc = counts[journal]
            else:
                jc = JournalCounter()
                counts[journal] = jc

            jc.totalCount += 1
            if s.isPositive():
                jc.positiveCount += 1
                nPos += 1
            else:
                jc.negativeCount += 1
                nNeg += 1

    nTotal = nPos + nNeg

    # Output report
    outputHeader = '\t'.join( \
                    [
                    'Journal',
                    'Articles',
                    '%',
                    sampleSet.getSampleClassNames()[sampleSet.getY_positive()],
                    '%',
                    sampleSet.getSampleClassNames()[sampleSet.getY_negative()],
                    '%',
                    ]) + '\n'
    sys.stdout.write(outputHeader)

    for j in sorted(list(counts.keys())):
        jc = counts[j]

        # get percentages, careful not to divide by zero counts
        posPercent = 0.0
        if nPos != 0: posPercent = float(100 * jc.positiveCount)/float(nPos)
        negPercent = 0.0
        if nNeg != 0: negPercent = float(100 * jc.negativeCount)/float(nNeg)

        output = '%s\t%d\t%6.2f\t%d\t%6.2f\t%d\t%6.2f\n' % ( \
                        j,
                        jc.totalCount,
                        float(100 * jc.totalCount)/float(nTotal),
                        jc.positiveCount,
                        posPercent,
                        jc.negativeCount,
                        negPercent,
                        )
        sys.stdout.write(output)

    # Totals
    output = '%s\t%d\t%6.2f\t%d\t%6.2f\t%d\t%6.2f\n' % ( \
                    'Totals',
                    nTotal,
                    100.0,
                    nPos,
                    100.0,
                    nNeg,
                    100.0,
                    )
    sys.stdout.write(output)

# ---------------------

def verbose(text):
    if args.verbose: sys.stderr.write(text)

# ---------------------
if __name__ == "__main__":
    main()
