#!/usr/bin/env python2.7 
#
# grab output from eutils "summary" via a post for pubmed IDs
#
# Output to stdout.
#
import sys
import string
import os
import time
import argparse
import json
import simpleURLLib as surl
import NCBIutilsLib as eulib

#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
			    description='get json records from pubmed')

    parser.add_argument('pmids', nargs=argparse.REMAINDER,
            help='pubmed IDs to retrieve')

    parser.add_argument('-f', '--format', dest='format', choices=['json','xml'],
	default='json', required=False, help="eutils output format")

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
	required=False, help="skip helpful messages to stderr")

    args = parser.parse_args()

    return args
#----------------------

args = parseCmdLine()

#----------------------
# Main prog
#----------------------
def main():
    retmode = args.format
    urlReader = surl.ThrottledURLReader( seconds=0.4 ) # don't overwhelm eutils

    resultsStr = eulib.getPostResults('pubmed', args.pmids,
				    URLReader = urlReader, op='summary',
				    rettype=None, retmode=retmode,) [0]
    if retmode == 'json':
	resultsJson = json.loads(resultsStr)
	print json.dumps(resultsJson,sort_keys=True,indent=4,
					separators=(',',': ')) + '\n'
    else:
	print resultsStr

# ---------------------

if __name__ == "__main__":
    main()
