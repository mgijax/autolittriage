#!/usr/bin/env python2.7 
#
# tdataTextCheck.py
#
# Look for specific terms/regular expressions in extracted text samples
#  to see if there are additional feature transformations to try.

import sys
import string
import os
import time
import argparse
import re


#-----------------------------------
# whole words
tumor
tumour
hepatoma
melanoma
teratoma
thymoma
neoplasia
neoplasm

# word endings
inoma
gioma
ocytoma
thelioma

# whole words or endings
adenoma
sarcoma
lymphoma
papilloma
leukemia
leukaemia
blastoma
lipoma
myoma
acanthoma
fibroma
glioma


searchRe = re.compile(r'\b([a-z]+oma)s?\b', re.IGNORECASE)
#-----------------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
    description='look for specific text in sample files')

    parser.add_argument('inputFiles', nargs=argparse.REMAINDER,
    	help='files of samples')

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
# Main prog
#----------------------
def main():

    startTime = time.time()

    # extend path up multiple parent dirs, hoping we can import sampleDataLib
    sys.path = ['/'.join(dots) for dots in [['..']*i for i in range(1,4)]] + \
		    sys.path
    import sampleDataLib

    recordSep = sampleDataLib.RECORDSEP

    numRecords = 0
    matchingText = {}	# { text : num times seen this matching text}

    ### Loop through all input files, reading all sample records.
    for fn in args.inputFiles:

	verbose("Reading %s\n" % fn)
	rcds = open(fn,'r').read().split(recordSep)	# read/split all rcds

	del rcds[-1]			# empty line at end after split()
	del rcds[0]			# delete header line from input

	for rcdnum, rcd in enumerate(rcds):
	    numRecords += 1
	    sr = sampleDataLib.SampleRecord(rcd)
	    rcdText = sr.getSampleAsText()
	    for m in searchRe.finditer(rcdText):
		if m:
		    mt = m.group(1).lower()
		    if matchingText.has_key(mt):
			matchingText[mt] += 1
		    else:
			matchingText[mt] = 1

    numMatches = 0
    for text in sorted(matchingText.keys()):
	count = matchingText[text]
	percent = float(100.0 * float(count)/numRecords)
	sys.stdout.write("'%s'\t%d\t%5.3f%%\n" % ( text, count, percent))
	numMatches += count

    sys.stdout.write("%d matches out of %d records\n" % \
					    (numMatches, numRecords))

    verbose( "Total time: %8.3f seconds\n\n" % (time.time()-startTime))
# ---------------------

def verbose(text):
    if args.verbose: sys.stderr.write(text)

# ---------------------
if __name__ == "__main__":
    main()
