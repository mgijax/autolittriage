#!/usr/bin/env python2.7 
#
# Library to support handling of lit triage text documents
#
import sys
import string
import re
import ConfigParser
import nltk.stem.snowball as nltk
#sys.path.extend(['..', '../..', '../../..'])
#from refSectionLib import RefSectionRemover
#-----------------------------------
cp = ConfigParser.ConfigParser()
cp.optionxform = str # make keys case sensitive

# generate a path up multiple parent directories to search for config file
cl = ['/'.join(l)+'/config.cfg' for l in [['.']]+[['..']*i for i in range(1,6)]]
cp.read(cl)

FIELDSEP    = eval( cp.get("DEFAULT", "FIELDSEP") )
RECORDSEP   = eval( cp.get("DEFAULT", "RECORDSEP") )

# CLASS_NAMES maps indexes to class names. CLASS_NAME[0] is 0th class name,etc.
CLASS_NAMES = eval( cp.get("DEFAULT", "CLASS_NAMES") )

# As is the sklearn convention we use
#  y_true to be the index of the known class of a sample (from training set)
#  y_pred is the index of the predicted class of a sample/record
#-----------------------------------

class SampleRecord (object):
    """
    Represents a training sample or a sample to predict.
    A training sample has a known class that it belongs to,
    A sample to predict may or may not have a known class (sometimes we
	do predictions on samples for which we know what class they belong to)
    Knows how to take a text representation of a record (typically a
	text string with delimitted fields) and parse into its fields
    Provides various methods to preprocess a sample record (if any)

    A SampleRecord can be marked as "reject". Has rejectReason, ...
    """
    def __init__(self, s,):

	self.rejected  = False
	self.rejectReason = None
	self.parseInput(s)
    #----------------------

    def parseInput(self, s):
	fields = s.split(FIELDSEP)

	if len(fields) == 6:	# have known class name as 1st field
	    self.knownClassName = fields[0]
	    fields = fields[1:]
	else:
	    self.knownClassName = None

	self.ID        = str(fields[0])
	self.isDiscard = str(fields[1])
	self.status    = fields[2]
	self.journal   = fields[3]
	self.doc       = self.constructDoc(fields[4])
    #----------------------

    def constructDoc(self, text):
	# Do what needs to be done to construct the text portion
	return text
    #----------------------

    def getSampleAsText(self):
	# return this record as a text string

	if self.rejected: return None

	if self.knownClassName:
	    fields = [self.knownClassName]
	else:
	    fields = []
	fields += [ self.ID,
		    self.isDiscard,
		    self.status,
		    self.journal,
		    self.doc,
		    ]
	return FIELDSEP.join( fields) + RECORDSEP
    #----------------------

    def getSampleName(self):
	return self.ID

    def getDiscard(self):
	return self.isDiscard

    def getStatus(self):
	return self.status

    def getJournal(self):
	return self.journal

    def getDocument(self):
	return self.doc

    def getKnownClassName(self):
	return self.knownClassName

    def isReject(self):
	return self.rejected

    def getRejectReason(self):
	return self.rejectReason

    #----------------------
    # "Preprocessor" functions.
    #  Each preprocessor should modify this sample and return itself
    #----------------------
#    refRemover = RefSectionRemover(maxFraction=0.4) # finds ref sections
#
#    def removeRefSection(self):
#	self.doc = SampleRecord.refRemover.getBody(self.doc)
#	return self
    # ---------------------------

    miceRegex = re.compile( r'\bmice\b', flags=re.IGNORECASE)

    def rejectIfNoMice(self):
	if not SampleRecord.miceRegex.search(self.doc):
	    self.rejected = True
	    self.rejectReason = "Mice not found"
	return self
    # ---------------------------

    urls_re = re.compile(r'\bhttps?://\S*',re.IGNORECASE) # match URLs
    token_re = re.compile(r'\b([a-z_]\w+)\b')	# match lower case words
    stemmer = nltk.EnglishStemmer()

    def removeURLsCleanStem(self):
	'''
	Remove URLs and punct, lower case everything,
	Convert '-/-' to 'mut_mut',
	Keep tokens that start w/ letter or _ and are 2 or more chars.
	Stem,
	Replace \n with spaces
	'''
	output = ''

	for s in SampleRecord.urls_re.split(self.doc): # split and remove URLs
	    s = s.replace('-/-', ' mut_mut ').lower()
	    for m in SampleRecord.token_re.finditer(s):
		output += " " + SampleRecord.stemmer.stem(m.group())
	self.doc = output
	return self
    # ---------------------------

    def removeURLs(self):
	'''
	Remove URLs, lower case everything,
	Convert '-/-' to 'mut_mut',
	'''
	output = ''

	for s in SampleRecord.urls_re.split(self.doc):
	    s = s.replace('-/-', ' mut_mut ').lower()
	    output += ' ' + s
	self.doc = output
	return self
    # ---------------------------

    def addJournalFeature(self):
	'''
	add the journal name as a text token to the document
	'''
	jtext = 'journal__' + '_'.join( self.journal.split(' ') ).lower()
	self.doc += " " + jtext
	return self

    # ---------------------------

    def truncateText(self):
	# for debugging, so you can see a sample record easily
	self.doc = self.doc[:50]
	return self
# end class SampleRecord ------------------------

class PredictionReporter (object):
    """
    Knows how to generate/format prediction reports for SampleRecords and their
    predictions from some model.

    Provides two types of reports
	a "short" prediction file with basic sample info + the prediction
	a longer prediction file that has additional info including the doc
	itself.

    Knows the structure of a SampleRecord.
    """

    rptFieldSep = '\t'

    def __init__(self,  exampleSample,		# an example SampleRecord
			hasConfidence=False,	# T/F the predicting model has
					    	#  confidences for predictions
			):
	# we assume if this exampleSample record has a knownClass, then
	#  all samples have a knownClass, and we should report that column
	self.exampleSample  = exampleSample
	self.knownClassName = exampleSample.getKnownClassName()
	self.hasConfidence  = hasConfidence

    def getPredHeaderColumns(self):
	# return list of column names for a header line
	cols = [ "ID" ]
	if self.exampleSample.knownClassName != None: cols.append("True Class")
	cols.append("Pred Class")
	if self.hasConfidence:
	    cols.append("Confidence")
	    cols.append("Abs Value")
	return cols

    def getPredOutputHeader(self):
	# return formatted header line for prediction report
	cols = self.getPredHeaderColumns()
	return self.rptFieldSep.join(cols) + '\n'

    def getPredLongOutputHeader(self):
	# return formatted header line for Long prediction report
	cols = self.getPredHeaderColumns()
	cols.append("isDiscard")
	cols.append("status")
	cols.append("journal")
	cols.append("Processed text")
	return self.rptFieldSep.join(cols) + '\n'

    def getPredictionColumns(self, sample, y_pred, confidence):
	# return list of values to output for the prediction for this sample
	# y_pred is the predicted class index, not the class name
	cols = [ sample.ID ]
	if self.knownClassName != None:  cols.append(sample.knownClassName)
	cols.append(CLASS_NAMES[y_pred])
	if self.hasConfidence:
	    if confidence != None:
		cols.append("%6.3f" % confidence)
		cols.append("%6.3f" % abs(confidence))
	    else:	# don't expect this would ever happen, but to be safe
		cols.append("none")
		cols.append("none")
	return cols

    def getPredOutput(self, sample, y_pred, confidence=None):
	# return formatted line for the prediction report for this sample
	# y_pred is the predicted class index, not the class name
	cols = self.getPredictionColumns(sample, y_pred, confidence)
	return self.rptFieldSep.join(cols) + '\n'

    def getPredLongOutput(self, sample, y_pred, confidence=None):
	# return formatted line for the Long prediction report for this sample
	# y_pred is the predicted class index, not the class name
	cols = self.getPredictionColumns(sample, y_pred, confidence)
	cols.append(sample.isDiscard)
	cols.append(sample.status)
	cols.append(str(sample.journal))
	cols.append(str(sample.doc))
	return self.rptFieldSep.join(cols) + '\n'
# end class PredictionReporter ----------------

def text2FigText(fulltext):
    """
    Take a fulltext doc and return the figure text within it.
    Figure text means:
	"Fig(ure) alphnumeric optional(.:)" at start of new paragraph
	(paragraph = \n\ntext..)
	or
	... figure or fig ... (case insensitive) in the middle of a paragraph.
	    take 50 words on either side ("word" = whitespace delimited space)
	    but stop at \n. don't overlap other fig text
    """
    captionRe = r'^^fig(ure)? \w+[.: ](.+)$$'	# match true figure caption
    discussRe = r''			# match figure discussion in text

    r = re.compile(captionRe, re.IGNORECASE | re.MULTILINE)


if __name__ == "__main__":
    r = SampleRecord(\
    'yes|pmID1|noDiscard|Indexed|my Journal|text text text text text Reference r1\n'
    )
    print r.getKnownClassName()
    print r.getSampleName()
    print r.getJournal()
    print r.isReject()
    print r.getDocument()
    print r.getSampleAsText(),
#    r.removeRefSection()
#    print r.getDocument()
    r.rejectIfNoMice()
    print r.isReject()
    print r.getRejectReason()
    r.addJournalFeature()
    print r.getDocument()
    print "Prediction Report:"
    rptr = PredictionReporter(r, hasConfidence=True)
    print rptr.getPredOutputHeader(),
    print rptr.getPredOutput(r, 0, confidence=-0.5)
