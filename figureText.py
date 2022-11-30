#!/usr/bin/env python3

"""
#######################################################################
Author:  Jim
Routines for extracting figure related text from articles
We treat tables as figures too.
As we refer to "figure caption" or "figure text" or "fig", we mean "tables" and
"table text" too.

Example Usage:
    converter = Text2FigConverter(conversionType='legCloseWords')
    for b in converter.text2FigText(text):
        print b  # a chunk of text that contains figure related text

To run automated tests:   python test_figureText.py [-v]

#######################################################################
"""

import re
from utilsLib import spacedOutRegex

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
                conversionType='legends', # which flavor discussed above:
                                        # 'legends', 'legParagraphs',
                                        #   'legCloseWords'
                numWords=50,		# if 'legCloseWords', how many words
                                        #   to include on each side of "fig"
                ):
        self.conversionType = conversionType
        if conversionType not in ['legends', 'legParagraphs', 'legCloseWords']:
            raise AttributeError("invalid text2fig conversion type '%s'\n" % \
                                                    self.conversionType)
        self.numWords = numWords

    def text2FigText(self, text,
        ):
        """
        Return list of figure/table text blurbs in text
        """
        if self.conversionType == 'legCloseWords':
            return text2FigText_LegendAndWords(text,self.numWords)
        elif self.conversionType == 'legends':
            return text2FigText_Legend(text)
        elif self.conversionType == 'legParagraphs':
            return text2FigText_LegendAndParagraph(text)
#---------------------------------

# Nomenclature:
# 'regex' = the text of a regular expression (as a string)
# 're'    = a regular expression object from the re module

PARAGRAPH_BOUNDARY = '\n\n'	# defines a paragraph boundary
PARAGRAPH_BOUNDARY_LEN = len(PARAGRAPH_BOUNDARY)

# match a word "figure" or "table" in various forms
#  i.e.,  "fig" or "figure" or "figures" or "table" or "tables"
figureRe = re.compile(r'\b(?:fig(?:ure)?|table)s?\b', re.IGNORECASE)

# match the words that can begin a figure or table legend.
#   i.e., "fig" or "figure" or "supp...figure" or "table"
#   Note no plurals
legendRe = re.compile(\
        r'\b(?:' +
            r'(?:' +  # words that sometimes preceed "Figure" "Table" in legend
                r'(?:' + r's[ ]*u[ ]*p[ ]*p[ ]*(?:\w|[ ])*' + r'|' +
                    spacedOutRegex('online')                + r'|' +
                    spacedOutRegex('extendeddata') + 
                r')\s+' +
            r')?' +
            r'(?:' +    # the base words that start a legend
                spacedOutRegex('figure') + r'|' +
                spacedOutRegex('fig') + r'|' +
                spacedOutRegex('table') +
            r')' +
        r')\b',
        re.IGNORECASE)

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

def text2FigText_LegendAndParagraph(text,):
    """
    Return list of paragraphs in text that talk about figures or tables
    (includes legends)
    """
    figParagraphs = []

    for p in paragraphIterator(text):
        if legendRe.match(p) or figureRe.search(p):
            figParagraphs.append(p)

    return figParagraphs
#---------------------------------

def text2FigText_LegendAndWords(text, numWords=50,):
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

def getFigureBlurbs(text, numWords=50,):
    """
    Search through text for references to figures/tables.
    Return a list of text blurbs consisting of numWords around those references
    """
    matches = list(figureRe.finditer(text))	# all matches of fig/tbl words

    if len(matches) == 0: return []

    blurbs = []				# text blurbs to return

    # 1st match, leading chunk before first fig/tbl word
    m = matches[0]
    textChunk = text[ : m.start() ]	# text before the fig/tbl word
    words = textChunk.split()		# the words

        # curBlurb is text so far of the numWords around the current
        #   match we are looking at
    curBlurb = ' '.join(words[-numWords:])	# Start w/ words before 1st m

    # for each match before last one,
    #   look at textChunks between fig word matches
    for i in range(len(matches)-1):
        textChunk = text[ matches[i].start() : matches[i+1].start() ]
        words = textChunk.split() 	# words incl 1st fig word but not 2nd

        # Have '...fig ... intervening text fig...',
        #   words[] are the words in   fig ...intervening text
        # Could have two blurbs:  words[:numWords] and words[-numWords:]
        # But if these two blurbs overlap, really only one blurb:
        #   the whole intervening text

        if numWords > (len(words)-1)/2:	# have overlap (-1: dont count fig word)
            curBlurb += ' ' + ' '.join(words)	# no blurb boundary yet

        else:				# have 2 blurbs & blurb boundary
            eoBlurbWords = ' '.join(words[:numWords+1]) # +1: incl 'fig' word
            curBlurb += ' ' + eoBlurbWords
            blurbs.append(curBlurb)			# save this blurb

            curBlurb = ' '.join(words[-numWords:]) 	# start new blurb

    # last match, trailing chunk after last fig/tbl word
    m = matches[len(matches) -1]
    textChunk = text[ m.start() : ]
    words = textChunk.split()
    curBlurb += ' ' + ' '.join(words[:numWords+1])	# +1: incl 'fig' word
    blurbs.append(curBlurb)

    return blurbs
#---------------------------------
