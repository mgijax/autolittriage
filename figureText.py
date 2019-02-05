#!/usr/bin/env python2.7

"""
#######################################################################
Author:  Jim
Routines for extracting figure related text from articles
Treating tables as figures too.
As we refer to "figure caption" or "figure text", we mean "tables" and
"table text" too.

Main function (example):
    for b in text2FigText(text)
	print b  # a chunk of text that contains figure related text
#######################################################################
"""

import re

#---------------------------------

PARAGRAPH_BOUNDARY = '\n\n'	# defines a paragraph boundary
PARAGRAPH_BOUNDARY_LEN = len(PARAGRAPH_BOUNDARY)

# match word "fig" or "figure" or "supp...figure" or "table" or "tables"
figureRe = re.compile(r'\b(?:(?:supp\w*[ ])?fig(?:ure)?|tables?)\b',
								re.IGNORECASE)
#---------------------------------

def text2FigText(text,
    ):
    """
    Return list of paragraphs in text that talk about figures or tables
    """
    figParagraphs = []		# list of fig paragraphs to return
    eoText = len(text)		# index of 1st char not in text

    startPara = 0

    while startPara != eoText:

	endPara = text.find(PARAGRAPH_BOUNDARY, startPara \
						    + PARAGRAPH_BOUNDARY_LEN)
	if endPara == -1:	# must be no more paragraph ends, at text end
	    endPara = eoText

	# just change to figureRe.match() to only match table/figure legends
	if figureRe.search(text, startPara, endPara):
	    figParagraphs.append( text[ startPara:endPara ] )

	startPara = endPara

    return figParagraphs

#---------------------------------

if __name__ == "__main__": 	# ad hoc test code
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
    if True:
	blurbs = text2FigText(testdoc)
	for b in blurbs:
	    print "****|%s|****" % b
    if True:
	simpleTestDoc = """
start of text. Fig 1 is really interesting, I mean it. Really.

Some intervening text. blah1 blah2 blah3 blah4 blah5 blah6

Figure 1: this is the caption 1. I really like it too.
and this is a bit more of the caption.

Some intervening text. this is suitable and should not match. Nor should 
gofigure

Some text about tables. blah blah.

Table: the start of a table

Figure 2: this is caption 2. Also spellbinding

Supplemental Figure 3: this is the caption of a supplemental figure.

here is a supp figure mention

And here is the end of this amazing document. Really it is over
"""
	blurbs = text2FigText(simpleTestDoc)
	for b in blurbs:
	    print "****|%s|****" % b
    if True:	# boundary conditions
	simpleTestDoc = "no paragraph start but figure\n\n"
	blurbs = text2FigText(simpleTestDoc)
	for b in blurbs:
	    print "****|%s|****" % b

	simpleTestDoc = "\n\nno paragraph end figure"
	blurbs = text2FigText(simpleTestDoc)
	for b in blurbs:
	    print "****|%s|****" % b

	simpleTestDoc = "no paragraph start or end figure"
	blurbs = text2FigText(simpleTestDoc)
	for b in blurbs:
	    print "****|%s|****" % b

	simpleTestDoc = ""
	print "empty string"
	blurbs = text2FigText(simpleTestDoc)
	for b in blurbs:
	    print "****|%s|****" % b

	simpleTestDoc = "s"
	print "one character"
	blurbs = text2FigText(simpleTestDoc)
	for b in blurbs:
	    print "****|%s|****" % b

	simpleTestDoc = "\n\n"
	print "only para boundary"
	blurbs = text2FigText(simpleTestDoc)
	for b in blurbs:
	    print "****|%s|****" % b
