#!/usr/bin/env python2.7

# Read a sample file from stdin and extract the sample record
#  for specified pubmed IDs. Write to stdout.
#
import sys
import argparse
import utilsLib

DEFAULT_SAMPLE_TYPE  = "BaseSample"

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='read article rcds from stdin & write selected rcds to stdout')

    parser.add_argument('pmids', nargs=argparse.REMAINDER,
	help='pubmed IDs for articles to select')

    parser.add_argument('--sampletype', dest='sampleObjTypeName',
	default=DEFAULT_SAMPLE_TYPE,
	help="Sample class name in sampleDataLib. Default: %s" \
							% DEFAULT_SAMPLE_TYPE)

    parser.add_argument('--justtext', dest='justText', action='store_true',
        help="output just the text of the article, not the full sample record")

    parser.add_argument('--oneline', dest='oneLine', action='store_true',
        help="smoosh article records into one line each.")

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
        required=False, help="include helpful messages to stderr")

    args = parser.parse_args()

    args.sampleFile = sys.stdin		# this could become an arg someday

    return args
#---------------------------

args = parseCmdLine()

def main():

    # extend path up multiple parent dirs, hoping we can import sampleDataLib
    sys.path = ['/'.join(dots) for dots in [['..']*i for i in range(1,8)]] + \
                    sys.path
    import sampleDataLib

    if not hasattr(sampleDataLib, args.sampleObjTypeName):
        sys.stderr.write("invalid sample class name '%s'" \
                                                    % args.sampleObjTypeName)
        exit(5)

    sampleObjType = getattr(sampleDataLib, args.sampleObjTypeName)
    verbose("Sample type '%s'\n" % args.sampleObjTypeName)

    sampleSet = sampleDataLib.SampleSet(sampleObjType)
    sampleSet.read(args.sampleFile)

    recordEnd = sampleSet.getRecordEnd()

    for rcdnum, sample in enumerate(sampleSet.sampleIterator()):

	if sample.getID() in args.pmids: 
	    verbose("ID '%s' found at record number %d\n" % \
						    (sample.getID(), rcdnum))
	    if args.justText:
		text = sample.getDocument()
	    else:
		text = sample.getSampleAsText()

	    if args.oneLine:
		text = text.replace('\n', ' ')

	    sys.stdout.write(text + recordEnd + '\n')
#---------------------------
def verbose(text):
    if args.verbose:
	sys.stderr.write(text)
	sys.stderr.flush()

if __name__ == "__main__":
    main()
