""" Author:  Jim, Sept 2018
    Convert downloaded PDF file names from PMID_nnnnn.pdf to PMCmmmmm.pdf
"""

import sys
import os
import os.path as osp
#import time
import argparse
#import runCommand
# --------------------------

def parseCmdLine():
    parser = argparse.ArgumentParser( \
	description= \
	'''rename pdf files from Pubmed ID to PMC IDs
	'''
	)
    parser.add_argument('dirs', nargs=argparse.REMAINDER,
	help="directories with pdf's")

    args = parser.parse_args()

    return args
# --------------------------


# --------------------------
# Main routine
# --------------------------
def process():

    args = parseCmdLine()
    m = IdMapper('/home/jak/work/Backpopulate/oa_file_list.txt')

    savedir = os.getcwd()
    for dir in args.dirs:
	os.chdir(dir)
	print dir
	for file in os.listdir('.'):
	    if file[-4:] == '.pdf' and file[:5] == 'PMID_':

		pmcId = m.pm2pmcId(file[5:-4])
		newfile = pmcId + '.pdf'

		#print '%s rename(%s, %s)' % (dir, file, newfile)
		os.rename(file,newfile)
	os.chdir(savedir)

# ---------------------
class IdMapper: 
    """provide mappings from PMID to PMC ID
    """
    def __init__(self, filename):
	""" filename is file holding the Open Access article list
	"""
	self.pm2pmc = {}
	fp = open(filename, 'r')
	fp.next()		# skip 1st line with date
	for line in fp:
	    parts = line.split('\t')
	    pmcId = parts[2].strip()
	    pmId = parts[3].strip()[5:]		# rip off "PMID:"
	    self.pm2pmc[pmId] = pmcId
    # ---------------------

    def pm2pmcId(self, pmId):
	return self.pm2pmc[pmId]
# ---------------------

if __name__ == "__main__": 
    process()
