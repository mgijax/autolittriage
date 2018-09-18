#!/usr/bin/python2.7

import sys
import argparse
import re
import os.path

# read lines from stdin that are from a tar tv command (= tar --list -v)

#  on linux, these lines look like:
#-rw-rw-r-- pmc/pmcdev 15103630 2017-04-01 21:19 PMC5334534/ACEL-16-281-s001.pdf
#  on MacOS, these lines look like:
#   a little different

# output the name of pdf that appears to be the true article PDF
#  (not a PDF that contains supplemental data)
# This logic appears to be somewhat journal specific :-(

def parseCmdLine():
    parser = argparse.ArgumentParser( \
	description= \
	'''output pdf file name that is the longest file in tar file
	'''
	)
    parser.add_argument('--macos', dest='os', action='store', default='linux',
	help="if running on MacOS (default is Linux)")

    args = parser.parse_args()
    return args
#--------------------

###################
# initialize
###################
args = parseCmdLine()

# for linux tar command:
file_len_part = 2		# which field in tar output has file len
# for macos tar command:
if args.os == 'macos':
    file_len_part = 4		# which field in tar output has file len

maxPDFlength = 0		# max length PDFs seen so far
mainPDFname   = ''		# full pathname within the tar file of the 
				#  desired PDF (of the PDFs seen so far)

# re to match probable main pdf filename (without .pdf)
main_re_string = r'.*main$|nihms[0-9]+$'
main_RE = re.compile(main_re_string, re.IGNORECASE)

# re to match probable supplemental data filenames (without .pdf)
supp_re_string = r'.*sup.*|.*sd.*|.*s[0-9]+$'
supp_RE = re.compile(supp_re_string, re.IGNORECASE)

###################
# scan through tar output lines
###################
for line in sys.stdin.readlines():	# for line in tar output
    l = line.strip()
    if l.endswith('.pdf'):
	parts          = l.split()
	file_len       = int(parts[file_len_part])
	path_name      = parts[-1]	# last is the pathname in the tar file
	base_file_name = os.path.basename(path_name).replace('.pdf', '')

	if re.match(main_RE, base_file_name):	# should be main pdf
	    mainPDFname = path_name
	    break
	if re.match(supp_RE, base_file_name):	# appears to be supp data pdf
	    continue
	if file_len > maxPDFlength:		# dunno, remember longest
	    maxPDFlength = file_len
	    mainPDFname = path_name

print mainPDFname
