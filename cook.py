#!/usr/bin/env python2.7 
#
"""
    cook.py
    Author: Jim Kadin

    Preprocess "raw" article text files down to "cooked" text files that
    we want to do feature extraction on.

    "Cooking" is a process that can be done one article/doc at a time, no need
    to look at multiple docs.

    Ultimately want a cooked output file for each input "raw" file.
    Plus a Report that looks like:
	pmid
	Y/N (relevant)
	journal
	# figs (found) Captions vs. fig discussion?
	length fig text
	length of cooked doc?
"""
import sys
import os
import glob
import argparse
import string
import time
#sys.path.append('..')
from figureText import text2FigText
#import db
#import sampleDataLib as sdlib
#from ConfigParser import ConfigParser
#import sampleDataLib as sdLib
#import sklearnHelperLib as ppLib	# module holding preprocessor function
##########################################################

RAW_EXTENSION = 'raw'			# file extension for raw docs
COOKED_EXTENSION = 'coo'		# for cooked docs

args = None
##########################################################

def getArgs():
    parser = argparse.ArgumentParser( \
    description='Cook raw article text files into cooked article text files')

    parser.add_argument('inputs', nargs=argparse.REMAINDER,
	help= \
	""" files or directories with raw files to cook.
	    For dirs, do all raw files in the dir.
	""")

#    parser.add_argument('inputFiles', action='store', 
#    	help='text input file')
#    parser.add_argument('-o', '--outputDir', dest='outputDir', action='store',
#	required=False, default=DEFAULT_OUTPUT_DIR,
#    	help='dir where /no and /yes go. Default=%s' % DEFAULT_OUTPUT_DIR)
#    parser.add_argument('-p', '--preprocessor', dest='preprocessor',
#	action='store', required=False, default=PREPROCESSOR,
#    	help='preprocessor function name. Default= %s' % PREPROCESSOR)

    parser.add_argument('--noWrite', dest='writeFiles',
        action='store_false', required=False,
        help="don't write any files, just report.")

    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
        help='print more messages')

    args = parser.parse_args()

    return args
##########################################################

def main():

    startTime = time.time()

    # rawFiles = the list of input file names to cook
    rawFiles = []
    for name in args.inputs:
	if os.path.isdir(name):
	    for fname in glob.glob('name/*.' + RAW_EXTENSION):
		rawFiles.append(fname)
	else:			# assume file
	    rawFiles.append(name)

    for name in rawFiles:
	verbose('\n*********\n' + name + '\n\n')

	with open(name, 'r') as fp:
	    article = fp.read()

	cookedText = cook(article)	# ******* cooking *******

	verbose(cookedText + '\n')

	if args.writeFiles:
	    root, ext = os.path.splitexp(name)
	    outName = root + '.' + COOKED_EXTENSION
	    with open(outName, 'w') as fp:
		fp.write(cookedText)

    endTime = time.time()
    verbose("%d files cooked. Total time: %8.3f seconds\n\n" % \
					    (len(rawFiles),endTime-startTime))
    return
##########################################################

def verbose(text):
    if args.verbose:
	sys.stdout.write(text)
##########################################################

def cook(text):
    cookedText = '\n\n'.join(text2FigText(text))
    return cookedText

##########################################################
if __name__ == "__main__":
    args = getArgs()
    main()
