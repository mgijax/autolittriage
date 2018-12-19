#!/usr/bin/env python2.7

"""
#######################################################################
Author:  Jim
Routines for transforming tokens in article text before training/predicting.
These transformations are intended to reduce dimensionality of the feature set
(i.e., lower the number of features) AND by collapsing different forms of tokens
that mean the same thing (or for which the different forms are not relevant for
classification), we should improve the classifier's accuracy.

Transformations include
    a) mapping/collapsing different tokens to a common one, e.g.,
	e1, e2, e3, ... --> embryonic_day
	ko, knock out   --> knockout

    b) deleting certain tokens that seem meaningless e.g., 
	a1, a2, ... (these are typically in text referring to Figure a, panel 1)

# Try to do this with only one pass through the text...

#######################################################################
"""

import sys
import re

def debug(text):
    if False: sys.stdout.write(text)

#---------------------------------

def findMatchingGroup(m):
    gd = m.groupdict()
    for k in gd.keys():
	if gd[k] != None:
	    return (k, m.start(k), m.end(k))
    return (None, None, None)	# shouldn't happen
#---------------------------------

class Mapping (object):
    def __init__(self, regex, replacement):
	self.regex = regex
	self.replacement = replacement

# dictionary of named mappings. Each mapping has a reg expr to find and a
# string to replace the text matching that reg expr.
# Thoughts:
# Might be better to define a dictionary of strings to map to the replacement
#   string.
#   This would mean more dictionary entries, one for each possible string rather
#   than a regex to match all the possible strings.
# BUT I'm worried about all the string slicing making lots of copies of
#  substrings as we process as strings may be long and there may be 10's of
#  thousands of strings to process.
# Using dictionary of mappings: cannot figure out how to split the source string
#  on the matching regex's AND know which regex matched. The regex.split()
#  method only returns the matching text, not the matching match object nor
#  the group. So cannot figure out which mapping object to apply
# Need to ponder all this further....

# tumors and tumor types - map all to "tumor_type"
# whole words
wholeWords = [
	    'tumor',
	    'tumour',
	    'hepatoma',
	    'melanoma',
	    'teratoma',
	    'thymoma',
	    'neoplasia',
	    'neoplasm',
	    ]
# word endings
endings = [
	    '[a-z]+inoma',
	    '[a-z]+gioma',
	    '[a-z]+ocytoma',
	    '[a-z]+thelioma',
	    ]
# whole words or endings
wordsOrEndings = [
	    '[a-z]*adenoma',
	    '[a-z]*sarcoma',
	    '[a-z]*lymphoma',
	    '[a-z]*papilloma',
	    '[a-z]*leukemia',
	    '[a-z]*leukaemia',
	    '[a-z]*blastoma',
	    '[a-z]*lipoma',
	    '[a-z]*myoma',
	    '[a-z]*acanthoma',
	    '[a-z]*fibroma',
	    '[a-z]*glioma',
	    ]
tumorRe = '|'.join( wholeWords + endings + wordsOrEndings )
tumorRe = '(?:' + tumorRe + ')s?'	# optional 's'

mappings = { 
    # mapping name: Mapping object
    'tt'   : Mapping( r'(?P<tt>' + tumorRe + ')', 'tumor_type'),

    'mice' : Mapping( r'(?P<mice>mouse|mous|murine)', 'mice'),
    #'mice' : Mapping( r'(?P<mice>mouse|mous|murine|mice)', ''), # ??

    'ko'   : Mapping( r'(?P<ko>ko|knock(?:ed|s)?(?:\s|-)?outs?)', 'knock_out'),
    'ki'   : Mapping( r'(?P<ki>knock(?:ed)?(?:\s|-)?ins?)', 'knock_in'),
    'gt'   : Mapping( r'(?P<gt>gene(?:\s|-)?trap(?:ped|s)?)', 'gene_trap'),
    'wt'   : Mapping( r'(?P<wt>wt|wild(?:\s|-)?types?)', 'wild_type'),
    'mut'  : Mapping( r'(?P<mut>\W*-/-\W*)', ' mut_mut '),

    'eday' : Mapping( r'(?P<eday>e[ ]?\d\d?|e(?:mbryonic)? day[ ]\d\d?)',
							    'embryonic_day'),
    'ee'   : Mapping( r'(?P<ee>(?:(?:[1,2,4,8]|one)(?:\s|-)cell)|blastocysts?)',
							    'early_embryo'),
    'fig'  : Mapping( r'(?P<fig>fig)', 'figure'),
    					
    # often refer to fig or panel A1, ...  should this be for all letters?
    # Should we do this at all?
    # (note e is part of embryonic day above)
    'letdig' : Mapping( r'(?P<letdig>[abcdfghs]\d)', ''),
    }

# combine all the mappings into 1 honking regex string
# OR them and word boundaries around
#bigRegex = r'\b' + '|'.join([ m.regex for m in mappings.values() ]) + r'\b'
bigRegex = '|'.join([ r'\b' + m.regex + r'\b' for m in mappings.values() ])

bigRe = re.compile(bigRegex, re.IGNORECASE)

def transformText(text):
    """
    Return the transformed text based on the transformations defined above.
    """
    toTransform = text
    transformed = ''

    debug( "initial: '%s'\n" % toTransform)

    while (True):		# loop for each regex match
	m = bigRe.search(toTransform)
	if not m: break		# no match found

	key, start, end = findMatchingGroup(m)

	debug( 'matching group: %s, %d, %d' % (key, start, end) + '\n')
	transformed += toTransform[:start] + mappings[key].replacement
	toTransform = toTransform[end:]
	debug( "transformed '%s'" % transformed + '\n')
	debug( "toTransform '%s'" % toTransform + '\n')
	debug('\n')

    transformed += toTransform
    debug("final string '%s'" % transformed + '\n')

    return transformed
#---------------------------------

if __name__ == "__main__":	# ad hoc tests
    if True:
	text = "...stuff then ko and knock out mouse and a wt mouse and more text"
	tests = [
		'before e12 after',
		'before E 1 after',
		'before E day 1 after',
		'before embryonic day 7 after',
		'before embryonic day 117 after',
		'before -/- e12. after',
		'before tumours and tumor after',
		'before fig s1 fig a23 g6 after',
		'before wildtypes wildtype wild type wt Wt wild\ntype wild-types after',
		'before knockout knocksouts knocked out knock out ko Ko knock\nout knock-outs after',
		'before knockin knockins knocked-in knock-in knocked in knock ins after',
		'before 1 cell 1-cell one-cell 2 cell 2-cell blastocyst after',
		'before genetrap genetraps gene trap gene-traps gene-trap gene-trapped gene trapped after',
		]

	for text in tests:
	    print text
	    print transformText(text)
	    print
    if True:
	tests = [	# tumor tests
		'adenoma fooadenoma xxxinoma xxxinomas neoplasm neoplasias'
		]

	for text in tests:
	    print text
	    print transformText(text)
	    print