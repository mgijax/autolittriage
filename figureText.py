#!/usr/bin/env python2.7

"""
#######################################################################
Author:  Jim
Routines for extracting figure related text from articles
We treat tables as figures too.
As we refer to "figure caption" or "figure text" or "fig", we mean "tables" and
"table text" too.

Example:
    converter = Text2FigConverter()
    for b in converter.text2FigText(text)
	print b  # a chunk of text that contains figure related text

#######################################################################
"""

import re

class Text2FigConverter (object):
    """
    IS an object that knows how to convert pieces of text into lists
       of strings that are figure/table legends and/or (parts of) paragraphs
       that refer to figures/tables.
    DOES: text2FigText('some text')

    3 flavors of conversion are supported:
	(1) just figure/table legends - paragraph starts with "figure"...
	(2) legends plus the text of any paragraph that contains "figure"...
	(3) legends plus n words around the reference to a fig/tbl (so not
	    the whole paragraph, just words close to "figure")
    """

    def __init__(self,
		conversionType='legend', # which flavor discussed above:
					# 'legend', 'paragraph', 'close words'
		numWords=50,		# if 'close words', how many close words
					#  to include on each side of "fig"
		):
	self.conversionType = conversionType
	self.numWords = numWords


    def text2FigText(self, text,
	):
	"""
	Return list of figure/table text blurbs in text
	"""
	if self.conversionType == 'legend':
	    return text2FigText_Legend(text)
	elif self.conversionType == 'paragraph':
	    return text2FigText_LegendAndParagraph(text)
	elif self.conversionType == 'close words':
	    return text2FigText_LegendAndWords(text,self.numWords)
	else:
	    raise AttributeError("invalid text2fig conversion type '%s'\n" % \
						    self.conversionType)

#---------------------------------

PARAGRAPH_BOUNDARY = '\n\n'	# defines a paragraph boundary
PARAGRAPH_BOUNDARY_LEN = len(PARAGRAPH_BOUNDARY)

# match a word "figure" or "table" in various forms
#  i.e.,  "fig" or "figure" or "figures" or "table" or "tables"
figureRe = re.compile(r'\b(?:fig(?:ure)?|table)s?\b', re.IGNORECASE)

# match a word that can begin a figure or table legend.
#   i.e., "fig" or "figure" or "supp...figure" or "table"
#   Note no plurals
legendRe = re.compile(r'\b(?:(?:supp\w*[ ])?fig(?:ure)?|table)\b',re.IGNORECASE)

#---------------------------------

def paragraphIterator(text,	# text (string) to search for paragraphs
    ):
    """iterate through the paragraphs in text
    """
    start = 0
    endPara = text.find(PARAGRAPH_BOUNDARY, start)
    while endPara != -1:
	yield text[start : endPara].strip()
	start = endPara + PARAGRAPH_BOUNDARY_LEN
	endPara = text.find(PARAGRAPH_BOUNDARY, start)
    yield text[start: ].strip()
#---------------------------------

def text2FigText_Legend(text,
    ):
    """
    Return list of paragraphs in text that are figure or table legends
    (paragraph starts with "fig" or "table")
    """
    return [ p for p in paragraphIterator(text) if legendRe.match(p) ]
#---------------------------------

def text2FigText_LegendAndParagraph(text,
    ):
    """
    Return list of paragraphs in text that talk about figures or tables
    (includes legends)
    """
    return [ p for p in paragraphIterator(text) if figureRe.search(p) ]
#---------------------------------

def text2FigText_LegendAndWords(text, numWords=50,
    ):
    """
    Return list of (full) legends and parts of paragraphs that talk about
      figures or tables
    The "parts" are defined by 'numWords' words surrounding figure/table
      references
    """
    figParagraphs = []

    for p in paragraphIterator(text):
	if legendRe.match(p):		# have figure/table legend
	    figParagraphs.append(p)
	else:				# not legend, get parts
	    figParagraphs += getFigureBlurbs(p, numWords)

    return figParagraphs
#---------------------------------

def getFigureBlurbs(text, numWords=50,
    ):
    """
    Search through text for references to figures/tables.
    Return a list of text blurbs consisting of numWords around those references
    """
    matches = list(figureRe.finditer(text))	# all matches of fig/tbl words

    if len(matches) == 0: return []

    blurbs = []				# text blurbs to return

    # 1st, leading chunk before first fig/tbl word
    m = matches[0]
    textChunk = text[ : m.start() ]	# text before the fig/tbl word
    words = textChunk.split()		# the words
    blurbs.append( ' '.join(words[-numWords:]) )

    # for textChunks between fig/tbl words
    for i in range(len(matches)-1):
	textChunk = text[ matches[i].start() : matches[i+1].start() ]
	words = textChunk.split()

	# Have '...fig intervening text fig...',
	#   words[] are the words in the intervening text.
	# Could have two blurbs:  words[:numWords] and words[-numWords:]
	# But if these two blurbs overlap, really only one blurb:
	#   the whole intervening text

	if numWords > len(words)/2:	# have overlap
	    blurbs.append( ' '.join(words) )	# use the whole chunk
	else:					# have two blurbs
	    blurbs.append( ' '.join(words[:numWords+1])) # +1: incl 'fig' ref
	    blurbs.append( ' '.join(words[-numWords:]) )

    # last, trailing chunk after last fig/tbl word
    m = matches[len(matches) -1]
    textChunk = text[ m.start() : ]
    words = textChunk.split()
    blurbs.append( ' '.join(words[:numWords+1]) ) # +1: incl 'fig' ref

    return blurbs

#---------------------------------
if __name__ == "__main__": 	# ad hoc test code
    testDoc = """
table paragraph 2 has a legend figure 1 blah0 blah1 blah2 blah3 blah4 fig 2 and more fig
"""
    if True:	# getFigureBlurbs()
	print " getFigureBlurbs()"
	blurbs = getFigureBlurbs(testDoc, numWords=2)
	for b in blurbs:
	    print "****|%s|****" % b

    simpleTestDoc = """
start of text. Fig 1 is really interesting, I mean it. Really.

Some intervening text. blah1 blah2 blah3 blah4 blah5 blah6

Figure 1: this is the caption 1. I really like it too.
and this is a bit more of the caption.

Some intervening text. this is suitable and should not match. Nor should 
gofigure

Figures can be helpful, but this is not a figure legend.

Some text about tables. blah blah.

Table: the start of a table

Figure 2: this is caption 2. Also spellbinding

Supplemental Figure 3: this is the caption of a supplemental figure.

here is a supp figure mention

And here is the end of this amazing document. Really it is over
"""
    if True:	# paragraphIterator
	testCases = [ 'abc\n\ndef ghi\n\nthe end',
		    '',
		    'abc def',
		    '\n\nabc def\n\n',
		    ]
	for text in testCases:
	    print '--------'
	    for p in paragraphIterator(text):
		print "'%s'" % p
    if True:	# Legend and Paragraphs

	print
	print "Text2FigConverter Just Legends"
	blurbs = Text2FigConverter().text2FigText(simpleTestDoc)
	for b in blurbs:
	    print b
	    print
	    #print "****|%s|****" % b

	print
	print "Text2FigConverter Legends and Paragraphs"
	blurbs = Text2FigConverter(conversionType="paragraph").text2FigText(simpleTestDoc)
	for b in blurbs:
	    print b
	    print
	    #print "****|%s|****" % b

	print
	print "Text2FigConverter Legends and Words"
	blurbs = Text2FigConverter(conversionType="close words", numWords=5).text2FigText(simpleTestDoc)
	for b in blurbs:
	    print "****|%s|****" % b
	    print
    if False:
	print "Should raise error"
	c = Text2FigConverter(conversionType='foo').text2FigText('text')


    if True:	# boundary conditions - Legend and Paragraphs
	print
	print "Boundary conditions in Legends and paragraphs"
	simpleTestDoc = "no paragraph start but figure\n\n"
	blurbs = text2FigText_LegendAndParagraph(simpleTestDoc)
	for b in blurbs:
	    print b
	print

	simpleTestDoc = "\n\nno paragraph end figure"
	blurbs = text2FigText_LegendAndParagraph(simpleTestDoc)
	for b in blurbs:
	    print b
	print

	simpleTestDoc = "no paragraph start or end figure"
	blurbs = text2FigText_LegendAndParagraph(simpleTestDoc)
	for b in blurbs:
	    print b
	print

	simpleTestDoc = ""
	print "empty string"
	blurbs = text2FigText_LegendAndParagraph(simpleTestDoc)
	for b in blurbs:
	    print b
	print

	simpleTestDoc = "s\n\n figure 1 blah\n\nD\n\n a fig sentence\n\nE"
	print "one character"
	blurbs = text2FigText_LegendAndParagraph(simpleTestDoc)
	for b in blurbs:
	    print b
	print

	simpleTestDoc = "\n\n"
	print "only para boundary"
	blurbs = text2FigText_LegendAndParagraph(simpleTestDoc)
	for b in blurbs:
	    print b
	print
