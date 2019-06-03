#!/usr/bin/env python2.7

# Read a sample file from stdin and extract the sample record
#  for a specified pubmed ID. Write to stdout.
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

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    args = parser.parse_args()

    args.sampleFile = sys.stdin	# set here in case we ever have input file opt

    return args
#---------------------------

args = parseCmdLine()

def main():

    # extend path up multiple parent dirs, hoping we can import sampleDataLib
    sys.path = ['/'.join(dots) for dots in [['..']*i for i in range(1,4)]] + \
                    sys.path
    import sampleDataLib

    recordSep = sampleDataLib.RECORDSEP

    rcds = args.sampleFile.read().split(recordSep)     # read/split all rcds
    del rcds[-1]		# empty line at end after spit()
    del rcds[0]                 # delete header line from input

    for rcdnum, rcd in enumerate(rcds):
	sr = sampleDataLib.SampleRecord(rcd)

	if sr.getID() in args.pmids: 
	    if args.justText:
		sys.stdout.write(sr.getDocument())
		sys.stdout.write(';;\n')
	    else:
		sys.stdout.write(sr.getSampleAsText())

if __name__ == "__main__":
    main()
