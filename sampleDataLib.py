#!/usr/bin/env python2.7 
#
# Library to support handling of lit triage text documents
#
import sys
import string
import re
import ConfigParser
import nltk.stem.snowball as nltk
import figureText
import featureTransform
#sys.path.extend(['..', '../..', '../../..'])
#from refSectionLib import RefSectionRemover
#-----------------------------------
cp = ConfigParser.ConfigParser()
cp.optionxform = str # make keys case sensitive

# generate a path up multiple parent directories to search for config file
cl = ['/'.join(l)+'/config.cfg' for l in [['.']]+[['..']*i for i in range(1,6)]]
cp.read(cl)

FIELDSEP     = eval( cp.get("DEFAULT", "FIELDSEP") )
RECORDSEP    = eval( cp.get("DEFAULT", "RECORDSEP") )
CLASS_NAMES  = eval( cp.get("CLASS_NAMES", "y_class_names") )

TEXT_PART_SEP = '::::\n'	# separates title, abstract, extr text

# As is the sklearn convention we use
#  y_true to be the index of the known class of a sample (from training set)
#  y_pred is the index of the predicted class of a sample/record

#-----------------------------------
# Regex's
miceRegex    = re.compile( r'\bmice\b', flags=re.IGNORECASE)
urls_re      = re.compile(r'\b(?:https?://|www[.])\S*',re.IGNORECASE)
token_re     = re.compile(r'\b([a-z_]\w+)\b',re.IGNORECASE)
className_re = re.compile(r'\b(\w+)\b')	# valid class names (all alpha numeric)

stemmer = nltk.EnglishStemmer()

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

	if len(fields) == 8:	# have known class name as 1st field
	    self.knownClassName = self.validateClassName(fields[0])
	    fields = fields[1:]
	else:
	    self.knownClassName = None

	self.ID            = str(fields[0])
	self.creation_date = str(fields[1])
	self.year          = str(fields[2])
	self.journal       = fields[3]
	self.title         = fields[4]
	self.abstract      = fields[5]
	self.extractedText = fields[6]
	
    #----------------------
    def validateClassName(self, name):
	"""
	Given the potential sample class 'name',
	1) transform it as needed: remove any leading/trailing spaces and punct
	2) validate the name is a CLASS_NAME
	Return the cleaned up name and set self.rejected if it is not valid.
	The need for this arose when using ';;' as the record sep and having
	   some extracted text ending in ';'. So splitting records on ';;'
	   left the record's class as ';discard' which caused problems down
	   the line.
	"""
	m = className_re.search(name)
	if m and m.group() in CLASS_NAMES:	# have match
	    return m.group()
	self.rejected = True
	self.rejectReason = "invalid class name '%s'" % (name)
	return name 
    #----------------------

    def constructDoc(self):
	# Do what needs to be done to construct the text doc
	# FIXME: not sure if we should joining with the TEXT_PART_SEP. But since
	#    we'd be  adding punctuation and we've likely already removed punct
	#    from the text files in other preprocessing steps. Hmmm...
	text = ' '.join([self.title, self.abstract,
						self.extractedText])
	return text
    #----------------------

    def getSampleAsText(self):
	# return this record as a text string

	if self.rejected: return None

	if self.knownClassName:
	    fields = [self.knownClassName]
	else:
	    fields = []

	# make sure title starts with '\n' so we can find the record boundaries
	#  during debugging
	#if self.title[0] == '\n': title = self.title
	#else: title = '\n' + self.title

	fields += [ self.ID,
		    self.creation_date,
		    self.year,
		    self.journal,
		    self.title,	
		    self.abstract,
		    self.extractedText,
		    ]
	return FIELDSEP.join( fields) + RECORDSEP
    #----------------------

    def getKnownClassName(self):
	return self.knownClassName

    def getKnownYvalue(self):
	return CLASS_NAMES.index(self.knownClassName)

    def getSampleName(self):
	return self.ID

    def getJournal(self):
	return self.journal

    def getTitle(self):
	return self.title

    def getAbstract(self):
	return self.abstract

    def getExtractedText(self):
	return self.extractedText

    def getDocument(self):
	return self.constructDoc()

    def isReject(self):
	return self.rejected

    def getRejectReason(self):
	return self.rejectReason

    #----------------------
    # "Preprocessor" functions.
    #  Each Preprocessor should modify this sample and return itself
    #----------------------
#    refRemover = RefSectionRemover(maxFraction=0.4) # finds ref sections
#
#    def removeRefSection(self):
#	self.doc = refRemover.getBody(self.doc)
#	return self
    # ---------------------------


    def rejectIfNoMice(self):	# preprocessor
				# might
	if not miceRegex.search(self.title + self.abstract +
							self.extractedText):
	    self.rejected = True
	    self.rejectReason = "Mice not found"
	return self
    # ---------------------------

    def figureText(self):	# preprocessor
	self.extractedText = ' '.join(figureText.text2FigText(self.extractedText))
	return self
    # ---------------------------

    def featureTransform(self):	# preprocessor
	self.title         = featureTransform.transformText(self.title)
	self.abstract      = featureTransform.transformText(self.abstract)
	self.extractedText = featureTransform.transformText(self.extractedText)
	return self
    # ---------------------------

    def removeURLsCleanStem(self):	# preprocessor
	'''
	Remove URLs and punct, lower case everything,
	Convert '-/-' to 'mut_mut',
	Keep tokens that start w/ letter or _ and are 2 or more chars.
	Stem,
	Replace \n with spaces
	'''
	#------
	def _removeURLsCleanStem(text):
	    output = ''
	    for s in urls_re.split(text): # split and remove URLs
		s = featureTransform.transformText(s).lower()
		for m in token_re.finditer(s):
		    # this would be the place to remove stop words or do
		    #  other token mappings, e.g., "e12" -> e_day
		    output += " " + stemmer.stem(m.group())
	    return  output
	#------

	self.title         = _removeURLsCleanStem(self.title)
	self.abstract      = _removeURLsCleanStem(self.abstract)
	self.extractedText = _removeURLsCleanStem(self.extractedText)
	return self
    # ---------------------------

    def removeURLs(self):	# preprocessor
	'''
	Remove URLs, lower case everything,
	'''
	#------
	def _removeURLs(text):
	    output = ''
	    for s in urls_re.split(text):
		output += ' ' + s.lower
	    return output
	#------

	self.title         = _removeURLs(self.title)
	self.abstract      = _removeURLs(self.abstract)
	self.extractedText = _removeURLs(self.extractedText)
	return self
    # ---------------------------

    def tokenPerLine(self):	# preprocessor
	"""
	Convert text to have one token per line.
	Makes it easier to examine the tokens/features
	FIXME: (?) maybe this should just break on whitespace and not tokenize
	    punctuation away ??
	"""
	#------
	def _tokenPerLine(text):
	    output = ''
	    for m in token_re.finditer(text):
		output += m.group().strip() + '\n'
	    return  output
	#------

	self.title         = _tokenPerLine(self.title)
	self.abstract      = _tokenPerLine(self.abstract)
	self.extractedText = _tokenPerLine(self.extractedText)
	return self
    # ---------------------------

    def addJournalFeature(self):	# preprocessor
	'''
	add the journal name as a text token to the document
	'''
	jtext = 'journal__' + '_'.join( self.journal.split(' ') ).lower()
	self.extractedText += " " + jtext
	return self
    # ---------------------------

    def truncateText(self):	# preprocessor
	# for debugging, so you can see a sample record easily
	
	self.title = self.title[:10].replace('\n',' ')
	self.abstract = self.abstract[:20].replace('\n',' ')
	self.extractedText = self.extractedText[:20].replace('\n',' ') + '\n'
	return self
# end class SampleRecord ------------------------

class PredictionReporter (object):

# NOT MODIFIED YET TO HANDLE AUTOMATED TRIAGE SAMPLES!
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

if __name__ == "__main__":
    r = SampleRecord(\
    '''keep|pmID1|01/01/1900|1900|my Journal|My Title|
    My Abstract|My text: text https://foo text www.foo.org text text text Reference r1'''
    )
    print r.getKnownClassName()
    print r.getKnownYvalue()
    print r.getSampleName()
    print r.getSampleAsText()
    exit(1)
#    print r.getJournal()
#    print r.isReject()
    print r.getDocument()
    print r.getSampleAsText()
#    r.removeRefSection()
#    print r.getDocument()
#    r.rejectIfNoMice()
#    print r.isReject()
#    print r.getRejectReason()
#    r.addJournalFeature()
    r.removeURLs()
    r.tokenPerLine()
    print r.getDocument()
#    print "Prediction Report:"
#    rptr = PredictionReporter(r, hasConfidence=True)
#    print rptr.getPredOutputHeader(),
#    print rptr.getPredOutput(r, 0, confidence=-0.5)
    r = SampleRecord(''';discard...|pmID1|10/3/2017|1901|journal|title|abstract|text''')
    print "Reject? %s " % str(r.isReject())
    print "Reason: " +  str(r.getRejectReason())
    print r.getKnownClassName()
    r = SampleRecord(''';foo...|pmID1|10/3/2017|1902|journal|title|abstract|text''')
    print "Reject? %s " % str(r.isReject())
    print "Reason: " +  str(r.getRejectReason())
    print r.getKnownClassName()

