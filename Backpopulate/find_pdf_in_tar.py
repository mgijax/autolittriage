import sys
import argparse
import re
import os
import os.path

# read lines from stdin that are from a tar tv command (= tar --list -v)

#  on linux, these lines look like:
#-rw-rw-r-- pmc/pmcdev 15103630 2017-04-01 21:19 PMC5334534/ACEL-16-281-s001.pdf
#  on MacOS, these lines look like:
#   a little different

# output the name of pdf that appears to be the true article PDF
#  (not a PDF that contains supplemental data)
# This logic appears to be somewhat journal specific :-(
#
# env variable "FIND_PDF_LOG" can be set to a filename to log to (append).
# The log records which pdf was chosen and why.
# This will give us a chance to see how well this works

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

###################
# initialize
###################
args = parseCmdLine()

if os.environ.has_key("FIND_PDF_LOG"):
    logFP = open(os.environ["FIND_PDF_LOG"], 'a')
else: logFP = None

# for linux tar command:
fileSizePart = 2		# which field in tar output has file len
# for macos tar command:
if args.os == 'macos':
    fileSizePart = 4		# which field in tar output has file len

maxPDFsize  = 0			# max size PDF seen so far
mainPDFname = ''		# full pathname within the tar file of the 
				#  desired PDF (of the PDFs seen so far)
reason = ''			# reason for the pdf file we've chosen.

# re to match probable main pdf basefilename (without .pdf)
main_re_string = '|'.join([
		    r'.*main$|.*article[-_]*[0-9]*$', # basic "main" pdfs
		    r'nihms[-_]*[0-9]+$',	# nih funded articles, I think
		    r'ncomms[0-9]+$',		# Nat Commun
		    r'onc[0-9]+a$',		# Oncogene
		    ])

#main_re_string = r'.*main$|nihms[-_]*[0-9]+$|.*article[-_]*[0-9]*$|ncomms[0-9]+$'
main_RE = re.compile(main_re_string, re.IGNORECASE)

# re to match probable supplemental data basefilenames (without .pdf)
supp_re_string = '|'.join([
		    r'.*sup.*',
		    r'.*sd.*',
		    r'.*s[0-9]+$',
		    r'.*data.*',
		    r'.*fig.*',
		    r'.*table.*',
		    r'.*video.*',
		    r'bj.*add$',	# Biochem J add'l data files
		    ])
#supp_re_string = r'.*sup.*|.*sd.*|.*s[0-9]+$|.*data.*|.*fig.*|.*table.*'
supp_RE = re.compile(supp_re_string, re.IGNORECASE)

###################
# scan through tar output lines
###################

pdfLines = []				# the tar output lines for pdf files 
for line in sys.stdin.readlines():	# for line in tar output
    l = line.strip()
    # remember dir path in case we are logging and don't find any pdfs
    dirPath = os.path.dirname( l.split()[-1] )

    if l.endswith('.pdf'): pdfLines.append(l)


pathNames = []				# all pdf pathnames
numNonSuppPathNames = 0
for l in pdfLines:
    parts         = l.split()
    fileSize      = int(parts[fileSizePart])
    pathName      = parts[-1]	# last is the pathname in the tar file
    pathNames.append(pathName)
    baseFileName = os.path.basename(pathName).replace('.pdf', '')

    if re.match(main_RE, baseFileName):	# should be main pdf
	mainPDFname = pathName
	reason = "m"			# we matched main PDF by name
	break
    if re.match(supp_RE, baseFileName):	# appears to be supp data pdf
	continue
    if fileSize > maxPDFsize:		# dunno, remember longest file
	# maybe we should find shortest fileNAME rather than longest file?
	# longest file seems to work ok
	maxPDFsize = fileSize
	mainPDFname = pathName
	numNonSuppPathNames += 1 
	if numNonSuppPathNames == 1:
	    reason = "o"		# only one
	else:
	    reason = "s"		# matched by file size

if logFP:
    if mainPDFname != '':	# chose a pdf filename
	# log the full path of the selected pdf and the basenames of the others
	pathNames.remove(mainPDFname)
	logFP.write("%s %s " % (reason,mainPDFname) )
	logFP.write( " ".join(map(os.path.basename, pathNames)) + '\n')

    else:			# no pdf filename selected
	logFP.write("  %s no PDF selected\n" % dirPath)

print mainPDFname
