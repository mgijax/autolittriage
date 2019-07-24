#!/usr/bin/env python2.7

# Read a sample file from stdin and extract the sample record
#  for specified pubmed IDs. Write to stdout.
#
import sys
import argparse
import sampleDataLib

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='retrieve sample records for pubmed IDs to stdout')

    parser.add_argument('pmids', nargs=argparse.REMAINDER,
	help='pubmed IDs for articles to retrieve')

    parser.add_argument('--justtext', dest='justText', action='store_true',
        help="output just the text of the article, not the full sample record")

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
        required=False, help="include helpful messages to stderr")

    args = parser.parse_args()

    args.sampleFile = sys.stdin	# might want input file to be an arg someday

    return args
#---------------------------

args = parseCmdLine()

def main():

    # extend path up multiple parent dirs, hoping we can import sampleDataLib
    sys.path = ['/'.join(dots) for dots in [['..']*i for i in range(1,4)]] + \
                    sys.path
    import sampleDataLib

    sampleSet = sampleDataLib.ClassifiedSampleSet().read(args.sampleFile)

    recordEnd = sampleSet.getRecordEnd()

    for rcdnum, sample in enumerate(sampleSet.sampleIterator()):

	if sample.getID() in args.pmids: 
	    verbose("ID '%s' found at record number %d\n" % \
							(sample.getID(), rcdnum))
	    if args.justText:
		sys.stdout.write(sample.getDocument() + '\n' + recordEnd)
	    else:
		sys.stdout.write(sample.getSampleAsText() + '\n' + recordEnd)

#---------------------------
def verbose(text):
    if args.verbose:
	sys.stderr.write(text)
	sys.stderr.flush()

if __name__ == "__main__":
    main()
