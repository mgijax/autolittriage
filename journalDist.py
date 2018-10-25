#!/usr/bin/env python2.7 
#
# journalDist.py
# Reads samples records from stdin and computes the journal counts/distribution 
#  across 3 sets:
#   all articles
#   discard articles
#   keep articles
# Write to stdout:
#  journalname all_count, discard_count, keep_count
#
# Assumes records are ';;' delimited with '|' between fields
#   1st field is discard/keep
#   5th field is journal
#
#
import sys
import string
import os
import time
import argparse

RECORD_SEP = ';;'
FIELD_SEP  = '|'
#-----------------------------------
#-----------------------------------

class JournalCounter (object):
    # has totalCount, discardCount, keepCount
    def __init__(self):
	self.totalCount   = 0
	self.discardCount = 0
	self.keepCount    = 0

#----------------------
# Main prog
#----------------------
def main():

    counts = {}		# counts[journal] is a JournalCounter
    nTotal   = 0	# num of articles/samples seen
    nDiscard = 0	# num of discard articles seen
    nKeep    = 0	# num of Keep articles seen

    rcds = sys.stdin.read().split(RECORD_SEP)

    for r in rcds:
	if len(r.strip()) == 0: continue
	DorK, f2, f3, f4, journal, leftovers = r.split(FIELD_SEP, 5)
	if journal == 'journal': continue	# skip header line(s)
	if counts.has_key(journal):
	    jc = counts[journal]
	else:
	    jc = JournalCounter()
	    counts[journal] = jc

	jc.totalCount += 1
	nTotal += 1
	if DorK == 'discard':
	    jc.discardCount += 1
	    nDiscard += 1
	else:
	    jc.keepCount += 1
	    nKeep += 1

    outputHeader = '\t'.join( \
		    [
		    'Journal',
		    'Total',
		    'Discard',
		    'Keep',
		    ]) + '\n'

    sys.stdout.write(outputHeader)

    for j in sorted(counts.keys()):
	jc = counts[j]
#	print jc.totalCount
#	print nTotal

	output = '%s\t%4.2f\t%4.2f\t%4.2f\n' % ( \
			j,
			float(100 * jc.totalCount)/float(nTotal),
			float(100 * jc.discardCount)/float(nDiscard),
			float(100 * jc.keepCount)/float(nKeep),
			)
	sys.stdout.write(output)

# ---------------------

def verbose(text):
    if args.verbose: sys.stderr.write(text)

# ---------------------
if __name__ == "__main__":
    main()
