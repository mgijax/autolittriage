#!/usr/bin/env python2.7

"""
#######################################################################
Author:  Jim
Routines for extracting figure related text from articles

Main function (example):
    for b in text2FigText(text)
	print b  # a chunk of text that contains figure related text
#######################################################################
"""

import re

#---------------------------------

PARAGRAPH_BOUNDARY = '\n\n'	# defines a paragraph boundary
PARAGRAPH_BOUNDARY_LEN = len(PARAGRAPH_BOUNDARY)

NUM_LEADING_WORDS  = 10		# words before 'fig' to grab as fig discu text
NUM_TRAILING_WORDS = 10		# words after 'fig' to grab as fig discu text

# match word "fig" or "figure" or "supp...figure"
figureRe = re.compile(r'\b(?:supp\w*[ ])?fig(?:ure)?\b', re.IGNORECASE )
#---------------------------------

def text2FigText(text,
		numLeading=NUM_LEADING_WORDS,
		numTrailing=NUM_TRAILING_WORDS,
    ):
    """
    Take text and return list of the non-overlapping "figure" text blurbs in it.
    The Figure text is after or around "fig(ure)" (case insensitive):

    If "fig(ure)" is at start of a paragraph, it is a caption
	so figure text goes from there to end of the paragraph

    FOR NOW, JUST DOING CAPTION TEXT
    If "fig(ure)" is NOT at start of a paragraph, it is discussion text
	so figure text goes from numLeading words before to numTrailing
	words after
	("word" = alphanumeric string, currently does not include '_')
	(Other Options to Consider
	    stop at paragraph boundaries
	    or take whole paragraphs or whole sentence,
	)
    Assumes: all figure text blurbs are NOT at beginning or end of text.
	    I.e., start after text[0] and end before text[len-1]
	    (otherwise, certain text indexing errors are possible)
    """
    start = 0			# position to start match from 
    prevBlurb = None		# most recent figure caption/discussion blurb
    figBlurbs = []		# list of figure text blurbs found

    while True:		# do searches for figure text until there are no more
	figMatch = figureRe.search(text, start)
	if not figMatch: break

	figWordStart = figMatch.start(0)
	figWordEnd   = figMatch.end(0)

	if atParaStart(text, figWordStart):	# caption
	    figBlurbStart = figWordStart
	    figBlurbEnd   = findParaEnd(text, figWordStart)
	    start = figBlurbEnd +1	# continue search after para

	else: 					# fig discussion text
	    figBlurbStart = findnWordsBefore(text, numLeading, figWordStart-1)
	    figBlurbEnd   = findnWordsAfter( text, numTrailing, figWordEnd+1)
	    start = figWordEnd +1	# continue search for after "figure"
	    				# since may find refs to other figures
					# with more trailing text to include
	    continue	# for now, skip fig discusison text, just do captions
	
	figBlurb = TextBlurb(text, start=figBlurbStart, end=figBlurbEnd)
	if len(figBlurbs) == 0:		# 1st blurb
	    prevBlurb = figBlurb
	    figBlurbs.append(prevBlurb)
	else:				# merge to prev, or add to figBlurbs
	    if not prevBlurb.mergeIfOverlap(figBlurb):
		figBlurbs.append(figBlurb)
		prevBlurb = figBlurb


    return [ fg.getText() for fg in figBlurbs ]
# ------------------------------

def atParaStart(text, start):
    """ Return True if text[start] is the start of a paragraph
    """
    if text[start-PARAGRAPH_BOUNDARY_LEN:start] == PARAGRAPH_BOUNDARY:
	return True
    return False
# ------------------------------
 
def findParaEnd(text, start):
    """
    Starting at text[start], find the end of the containing paragraph.
    Return the index in text of the last char of that paragraph
	(the char before PARAGRAPH_BOUNDARY)
    """
    eop = text.find(PARAGRAPH_BOUNDARY, start)	# idx of 1st char of boundary
    if eop == -1: 		# hmm, end of text before eop, what to do

	# find (up to) 100 words after and call that the paragraph end.
	# could go to end of text instead?
	eop = findnWordsAfter(text, 100, start)
    else:
	eop -= 1		# adjust to last char of paragraph

    return eop
# ------------------------------

def findnWordsAfter(text, n, start):
    """
    Starting at text[ start ],
    Return the index of the end of the nth word after that.
    If there are fewer than n words after start, return the index of the end
      of the last one.
    Future: could stop at paragraph boundaries, but keep it simple for now
    """
    indexOfLast = len(text) -1
    i = start			# i = spot to begin search for next word
    for w in range(n):
	wordEnd = findWordEnd(text, i)
	if wordEnd == -1 or wordEnd == indexOfLast:
	    return indexOfLast
	i = wordEnd +1

    return wordEnd
# ------------------------------

def findnWordsBefore(text, n, start):
    """
    Starting at text[ start ],
    Return the index of the start of the nth word before that.
    If there are fewer than n words before start, return the index of the start
      of the last one.
    Future: could stop at paragraph boundaries, but keep it simple for now
    """
    indexOfFirst = 0
    i = start			# i = spot to begin search for prev word
    for w in range(n):
	wordStart = findWordStart(text, i)
	if wordStart == -1 or wordStart == indexOfFirst:
	    return indexOfFirst
	i = wordStart -1

    return wordStart
# ------------------------------
def findWordEnd(text, start):
    """
    Starting at text[start],
    Find the end of the nearest word and return the index of that character.
    "Words" are contiguous strings of letters, digits.
    If there are no word ends in text after start, return -1
    Assumes: 0 <= start < len(text)
    e.g., 
    findWordEnd("this is text", 2) returns 3
    findWordEnd("this is text", 3) returns 3
    findWordEnd("this, is-text", 4) returns 7
    findWordEnd("this, is", 4) returns 7
    """
    i = start
    lastIndex = len(text) -1
    # if not in a word, find start of next one
    while( i < lastIndex and not text[i].isalnum()):
	i += 1

    if not text[i].isalnum(): return -1 	# didn't find word start

    # find end of this word
    while( i < lastIndex and text[i].isalnum()):
	if not text[i+1].isalnum():
	    break
	i += 1
    return i
# ------------------------------

def findWordStart(text, start):
    """
    Starting at text[start],
    Find the beginning of the nearest word and return the index of that char.
    "Words" are contiguous strings of letters, digits.
    If there are no word beginnings in text before start, return -1
    Assumes: 0 <= start < len(text)
    e.g., 
    findWordStart("this is text", 2) returns 0
    findWordStart("this is text", 5) returns 5
    findWordStart("this, is-text", 4) returns 0
    findWordStart("this, is", 7) returns 6
    """
    i = start
    earliestIndex = 0
    # if not in a word, find end of prev one
    while( i > earliestIndex and not text[i].isalnum()):
	i -= 1

    if not text[i].isalnum(): return -1		# didn't find word end

    # find end of this word
    while( i > earliestIndex and text[i].isalnum()):
	if not text[i-1].isalnum():
	    break
	i -= 1
    return i
# ------------------------------

class TextBlurb (object):
    """
    Is:   a substring of a piece of text
    Has:  the text string, the start and end index of the substring
    Does: support merging of textBlurbs
    """
    def __init__(self, text, start=0, end=None):
	"""
	Assumes: 0 <= end < len(text) (if not None)
		 0 <= start < len(text)
	"""
	self.text  = text
	self.start = start
	if end == None: end = len(text)-1
	self.end   = end

    def getText(self):
	return self.text[self.start:self.end+1]

    def overlaps(self, other):
	""" Return True if other and self overlap
	"""
	if  (self.text == other.text) and \
	    ((self.start  <= other.start and self.end >= other.start) or \
	     (other.start <= self.start  and other.end >= self.start)):
	    return True
	return False

    def mergeIfOverlap(self, otherBlurb):
	""" Merge otherBlurb into self if they overlap
	    Return True if we did merge, False otherwise
	"""
	if self.overlaps(otherBlurb):
	    self.start = min(self.start, otherBlurb.start)
	    self.end   = max(self.end, otherBlurb.end)
	    return True
	return False
# end class TextBlurb --------------------


if __name__ == "__main__":
    testdoc = """
in large part, through CMA, as genetic
blockage of this pathway almost completely abolished lysosomal
degradation of WT tau and led to its accumulation (Fig. 1a,b; GAPDH
is shown as an example of a well-characterized CMA substrate (Aniento
et al., 1993) known to accumulate intracellularly
Tau-A152T displayed very similar degradation
dynamics, although this mutation slightly reduced tau''s rates of
lysosomal degradation (20% inhibition) when compared with WT tau
(Fig. 1a,b). Blockage of CMA in cells expressing tau-A152T also resulted
in significant accumulation of this variant and ablated its lysosomal
degradation, suggesting preferential degradation
mutation severely impaired lysosomal uptake of tau by CMA, resulting in

Fig. 1 Contribution of CMA to degradation of disease-related mutant tau proteins. (a) Immunoblots for the indicated proteins of the mouse neuroblastoma cell line Neuro2a (N2a) control or knockdown for LAMP2A (siL2A) expressing under the control of a tetracycline promoter tau wild-type (WT) or tau mutated at residues A152T or P301L.
    Cells were treated with doxycycline to activate protein expression for 72 h and, where indicated, NH4Cl 20 mM and leupeptin 100 lM (N/L) were added during the last 4 h of
    incubation. LC3-II levels are shown as positive control of the effect of the inhibitors. GAPDH is shown as an example of well-characterized CMA substrate. Actin is shown for
    normalization purposes (note that lower relative contribution of actin in the same amount of total protein loaded is a consequence of the accumulation of proteins no longer
    degraded when CMA is blocked). (b) Quantification of tau levels normalized to actin. Values are expressed relative to those in untreated control cells that were given an
    arbitrary value of 1. n = 5. Differences after adding N/L (*), upon siRNA (#) or of the mutant tau proteins relative to WT () were significant for *,#,P < 0.05 and **,
    ##,P < 0.01. (c) Immunoblots for tau of isolated CMA-active lysosomes, pretreated or not with protease inhibitors (PI) for 10 min at 4 C and then incubated with the
    indicated tau proteins at 37 C for 20 min. Inpt: input (0.1 lg). (d) Quantification of binding (left) and uptake (right) of tau proteins by the CMA-active lysosomes. Values are
    indicated in ng, and were calculated from the densitometric quantification of a known amount of purified protein. n = 5. (e) Immunoblot for tau proteins incubated under
    the same condition as in c but with CMA-inactive (A) lysosomes. Input = 0.1 lg. All values are mean AE SEM. Differences with hTau40 WT were significant for *P < 0.05.

To further elucidate the contribution of CMA to the degradation of
the two mutants in the absence of any other proteolytic system, we used
a well-established in vitro system that allows to recapitulate different
CMA steps (binding and translocation of substrates) using isolated intact
lysosomes (Kaushik & Cuervo, 2009). We presented lysosomes with
either purified WT, A152T, or P301L tau and incubated them in the
presence or absence of protease inhibitors to block tau degradation
(Fig. 1c,d). This allows determining lysosomal binding of tau as the
amount of tau at the end of the incubation associated with the group of
lysosomes not pretreated with protease inhibitors, as internalized tau
would be rapidly degraded. Uptake of tau was calculated by the
difference between the amount of tau associated with lysosomes

could be secreted into exosomes. However, intracellular levels of tauP301L are not affected by disruption of multivesicular body/exosome
formation. It is possible that instead of our proposed release of

 2017 The Authors. Aging Cell published by the Anatomical Society and John Wiley & Sons Ltd.

Autophagy and pathogenic tau proteins, B. Caballero et al. 13 of 17

Fig. 7 Effect of oxidation and pseudophosphorylation on the degradation of tau by selective autophagic pathways. (a) Immunoblots for tau of isolated CMA-active
lysosomes, pretreated or not with protease inhibitors (PI) for 10 min at 4 C and then incubated with tau with cysteine 291 and 322 replaced by alanine (hTau40 C291A/
C322A), or with mutations S199E+S292E+T214E (AT8 site), plus T212E+S214E (AT100) plus S396E+S404E (PHF-1) (to yield htau40 AT8/AT100/PHF-1), with serine 262, 293,
324, and 356 replaced by glutamic acid (4xKXGE) (to mimic hyperphosphorylation) or with alanine (4xKXGA) (to disrupt phosphorylation). Proteins were added at the
indicated concentrations and incubations were performed at 37 C for 20 min. Inpt: input. (b) Quantification of binding (left) and uptake (right) of the tau proteins by the
CMA-active lysosomes. Values are indicated in ng, calculated from the densitometric quantification of a known amount of purified protein. n = 3. (c) Immunoblot of tau
proteins incubated under the same condition as in b but with rat CMA-inactive (A) lysosomes. (d) Immunoblots for tau in isolated rat late endosomes pretreated or not with
protease inhibitors (PI) for 10 min at 4 C and then incubated with the indicated tau proteins (0.5 lg) at 37 C for 30 min. (e) Quantification of binding, association, and
uptake/degradation of tau proteins by the late endosomes. Values are indicated as percentage of the input, calculated from the densitometric quantification of a known
amount of purified protein. n = 3. All values are mean AE SEM. Differences with hTau40 WT (*) or between the mutants (#) were significant for *P < 0.05 and **P < 0.001.
(f) Scheme of the steps of CMA disrupted for each of the indicated tau variants. 1. Targeting; 2. binding; 3. internalization; and 4. degradation. (g) Scheme of the steps of
e-MI disrupted for each of the indicated tau variants. 1. Targeting; 2. binding; 3. internalization; and 4. degradation.
tau-P301L via LE and exosomes, other systems contribute to tau-P301L


"""
    # Random, disorganized tests
    if False:
	text2FigText(testdoc)
    if False:
	e = findWordEnd("it is...", 1)
	print e
	e = findnWordsAfter("..it is here..", 2, 2)
	print e
	e = findnWordsAfter("text", 50, 0)
	print e
	e = findnWordsAfter("text", 50, 3)
	print e
	e = findnWordsAfter("text..", 50, 3)
	print e
    if False:
	e = findWordStart("..it is...", 4)
	print e
	e = findnWordsBefore("..it is here...", 2, 9)
	print e
	e = findnWordsBefore("text", 50, 3)
	print e
	e = findnWordsBefore("..text..", 50, 4)
	print e
    if False:
	text = ";;some.. text!"
	s = 0
	e = findWordEnd(text, s)
	print "word end: %d  '%s'" % (e,  text[s:e+1])

	s = 2
	e = findWordEnd(text, s)
	print "word end: %d  '%s'" % (e,  text[s:e+1])

	s = 5
	e = findWordEnd(text, s)
	print "word end: %d  '%s'" % (e,  text[s:e+1])

	s = 6
	e = findWordEnd(text, s)
	print "word end: %d  '%s'" % (e,  text[s:e+1])

	s = 13
	e = findWordEnd(text, s)
	print "word end: %d  '%s'" % (e,  text[s:e+1])
    if False:
	b1 = TextBlurb("some text", start=1, end=3)

	b2 = TextBlurb("some text", start=0, end=0)
	print "Overlap should false: " + str(b1.overlaps(b2))
	b2 = TextBlurb("some text", start=4, )
	print "Overlap should false: " + str(b1.overlaps(b2))
	b2 = TextBlurb("some text", start=0, end=1 )
	print "Overlap should true: " + str(b1.overlaps(b2))
	b2 = TextBlurb("some text", start=0, end=5 )
	print "Overlap should true: " + str(b1.overlaps(b2))

	b1.mergeIfOverlap(b2)
	print b1.getText()
    if True:
	simpleTestDoc = """
start of text. Fig 1 is really interesting, I mean it. Really.

Some intervening text. blah1 blah2 blah3 blah4 blah5 blah6

Figure 1: this is the caption 1. I really like it too.
and this is a bit more of the caption.

Some intervening text. blah1 blah2 blah3 blah4 blah5 blah6

Figure 2: this is caption 2. Also spellbinding

Supplemental Figure 3: this is the caption of a supplemental figure.

Supp Fig 4: here is another supp figure caption

Here is some discussion of figure 1 and discussion of figure 2. This should
overlap. but, But! But! Blah, this figure 2 discussion should not overlap

And here is the end of this amazing document. Really it is over
"""
	blurbs = text2FigText(simpleTestDoc, numLeading=50, numTrailing=50)
	for b in blurbs:
	    print "**** %s ****" % b
