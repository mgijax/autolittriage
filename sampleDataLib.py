#!/usr/bin/env python2.7 
#
# Library to support handling of lit triage samples (training samples or
#  samples to predict)
#
import sys
import string
import re
import ConfigParser
import figureText
import featureTransform
#-----------------------------------
cp = ConfigParser.ConfigParser()
cp.optionxform = str # make keys case sensitive

# generate a path up multiple parent directories to search for config file
cl = ['/'.join(l)+'/config.cfg' for l in [['.']]+[['..']*i for i in range(1,6)]]
cp.read(cl)

FIELDSEP     = eval( cp.get("DEFAULT", "FIELDSEP") )
RECORDEND    = eval( cp.get("DEFAULT", "RECORDEND") )
CLASS_NAMES  = eval( cp.get("CLASS_NAMES", "y_class_names") )

FIG_CONVERSION        = cp.get("DEFAULT", "FIG_CONVERSION")
FIG_CONVERSION_NWORDS = cp.getint("DEFAULT", "FIG_CONVERSION_NWORDS")
figConverter = figureText.Text2FigConverter(conversionType=FIG_CONVERSION,
						numWords=FIG_CONVERSION_NWORDS)

class ClassifiedSampleSet (object):
    """
    IS:     a set of ClassifiedSamples records
    HAS:    sample record list, ...
    DOES:   Loads/parses sample records from a sample record file
	    Writes sample records to a file

    Note: might want to implement a way to iterate through Samples so not all
	are held in memory at a time. Particularly if outside of this class,
	we are pulling each of the sample docs into a list or data structure,
	since then we'd be storing the text of each document twice.
	Could write an iterator that uses input file iterator to just get the
	next Sample (kind of a pain since we'd have to buffer lines until a
	Sample record sep is found).
	Or perhaps a way to say "kill/truncate a Sample" after it is used
	by the caller.
	For now, lets not worry and hope garbage collection takes care of 
	things ok.
    """
    def __init__(self,):
	self.samples = []
    #-------------------------

    def read(self, inFile,	# file pathname or open file obj for reading
	):
	"""
	Assumes sample record file is not empty and has a header line
	"""
	if type(inFile) == type(''): fp = open(inFile, 'r')
	else: fp = inFile

	self.textToSamples(fp.read())
	return self
    #-------------------------

    def textToSamples(self, text,
	):
	rcds = text.split(RECORDEND)
	del rcds[0]             # header line
	del rcds[-1]            # empty string after end of split

	self.samples = [ ClassifiedSample().parseInput(sr) for sr in rcds ]
	return self
    #-------------------------

    def write(self, outFile,	# file pathname or open file obj for writing
	writeHeader=True,	# write header line?
	):
	if type(outFile) == type(''): fp = open(outFile, 'w')
	else: fp = outFile

	if writeHeader:  fp.write(self.getHeaderLine() + RECORDEND)

	for s in self.samples:
	    fp.write(s.getSampleAsText() + RECORDEND)
	return self
    #-------------------------

    def addSample(self, sample,		# ClassifiedSample
	):
	if not isinstance(sample, ClassifiedSample):
	    raise TypeError('Invalid sample type %s' % str(type(sample)))
	self.samples.append(sample)
	return self
    #-------------------------

    def getSamples(self):		return self.samples
    def getNumSamples(self):		return len(self.samples)
    def getRecordEnd(self):		return RECORDEND
    def getHeaderLine(self):
	return ClassifiedSample.getHeaderLine()
    def getExtraInfoFieldNames(self):
	return ClassifiedSample.getExtraInfoFieldNames()

# end class ClassifiedSampleSet -----------------------------------

#-----------------------------------
# Regex's preprocessors
urls_re      = re.compile(r'\b(?:https?://|www[.]|doi)\S*',re.IGNORECASE)
token_re     = re.compile(r'\b([a-z_]\w+)\b',re.IGNORECASE)

stemmer = None		# see preprocessor below
#-----------------------------------

class BaseSample (object):
    """
    Represents a training sample or a sample to predict.
    A training sample has a known class that it belongs to,
    A sample to predict does not have a known class

    Provides various methods to preprocess a sample record
    (preprocess the text prior to vectorization)
    """
    def __init__(self,):
	pass
    #----------------------

    def constructDoc(self):
	return '\n'.join([self.title, self.abstract, self.extractedText])

    #----------------------
    def getSampleName(self):	return self.ID
    def getSampleID(self):	return self.getSampleName()
    def getID(self):		return self.getSampleName()
    def getName(self):		return self.getSampleName()

    def getTitle(self):		return self.title
    def getAbstract(self):	return self.abstract
    def getExtractedText(self): return self.extractedText
    def getDocument(self):	return self.constructDoc()
    #----------------------

    # preprocessSamples.py script checks for rejected samples.
    #  For autolittriage, we don't have any checks to reject samples (yet)
    def isReject(self):		return False
    def getRejectReason(self):	return None
    #----------------------

    #----------------------
    # "preprocessor" functions.
    #  Each preprocessor should modify this sample and return itself
    #----------------------

    def figureText(self):		# preprocessor
	self.extractedText = '\n'.join( \
			    figConverter.text2FigText(self.extractedText))
	return self
    # ---------------------------

    def featureTransform(self):		# preprocessor
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
	# This is currently the only preprocessor that uses a stemmer.
	# Would be clearer to import and instantiate one stemmer above,
	# BUT that requires nltk (via anaconda) to be installed on each
	# server we use. This is currently not installed on our linux servers
	# By importing here, we can use BaseSample in situations where we don't
	# call this preprocessor, and it will work on our current server setup.
	global stemmer
	if not stemmer:
	    import nltk.stem.snowball as nltk
	    stemmer = nltk.EnglishStemmer()
	#------
	def _removeURLsCleanStem(text):
	    output = ''
	    for s in urls_re.split(text): # split and remove URLs
		s = featureTransform.transformText(s).lower()
		for m in token_re.finditer(s):
		    output += " " + stemmer.stem(m.group())
	    return  output
	#------

	self.title         = _removeURLsCleanStem(self.title)
	self.abstract      = _removeURLsCleanStem(self.abstract)
	self.extractedText = _removeURLsCleanStem(self.extractedText)
	return self
    # ---------------------------

    def removeURLs(self):		# preprocessor
	'''
	Remove URLs, lower case everything,
	'''
	#------
	def _removeURLs(text):
	    output = ''
	    for s in urls_re.split(text):
		output += ' ' + s.lower()
	    return output
	#------
	self.title         = _removeURLs(self.title)
	self.abstract      = _removeURLs(self.abstract)
	self.extractedText = _removeURLs(self.extractedText)
	return self
    # ---------------------------

    def tokenPerLine(self):		# preprocessor
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

    def truncateText(self):		# preprocessor
	""" for debugging, so you can see a sample record easily"""
	
	self.title = self.title[:10].replace('\n',' ')
	self.abstract = self.abstract[:20].replace('\n',' ')
	self.extractedText = self.extractedText[:20].replace('\n',' ') + '\n'
	return self
    # ---------------------------

    def removeText(self):		# preprocessor
	""" for debugging, so you can see a sample record easily"""
	
	self.title = self.title[:10].replace('\n',' ')
	self.abstract = 'abstract...'
	self.extractedText = 'extracted text...\n'
	return self
# end class BaseSample ------------------------

class ClassifiedSample (BaseSample):
    """
    Represents a training sample that has a known classification (keep/discard)
    Knows how to take a text representation of a record (a text string with
	delimitted fields) and parse into its fields
    Has "extraInfoFields", information about the sample that don't necessarily
	relate to the sample features used for training/prediction, but may
	be used to subset the sample set when analyzing prediction results.
	(e.g., if we want to analyze precision/recall for individual journals)
    """
    # fields of a sample as an input/output record (as text), in order
    fieldNames = [ \
	    'knownClassName',
	    'ID'            ,
	    'creationDate'  ,
	    'year'          ,
	    'isReview'      ,
	    'refType'       ,
	    'suppStatus'    ,
	    'apStatus'      ,
	    'gxdStatus'     ,
	    'goStatus'      ,
	    'tumorStatus'   ,
	    'qtlStatus'     ,
	    'journal'       ,
	    'title'         ,
	    'abstract'      ,
	    'extractedText' ,
	    ]
    extraInfoFieldNames = [ \
	    'creationDate'  ,
	    'year'          ,
	    'isReview'      ,
	    'refType'       ,
	    'suppStatus'    ,
	    'apStatus'      ,
	    'gxdStatus'     ,
	    'goStatus'      ,
	    'tumorStatus'   ,
	    'qtlStatus'     ,
	    'journal'       ,
	    ]

    def __init__(self,):
	super(type(self), self).__init__()
    #----------------------

    def setFields(self, values,		# dict
	):
	self.knownClassName = self.validateClassName(values['knownClassName'])
	self.ID             = str(values['ID'])
	self.creationDate   = str(values['creationDate'])
	self.year           = str(values['year'])
	self.isReview       = str(values[ 'isReview' ])
	self.refType        = values[ 'refType' ]
	self.suppStatus     = values[ 'suppStatus' ]
	self.apStatus       = values[ 'apStatus' ]
	self.gxdStatus      = values[ 'gxdStatus' ]
	self.goStatus       = values[ 'goStatus' ]
	self.tumorStatus    = values[ 'tumorStatus' ]
	self.qtlStatus      = values[ 'qtlStatus' ]
	self.journal        = values[ 'journal']
	self.title          = values[ 'title']
	self.abstract       = values[ 'abstract']
	self.extractedText  = values[ 'extractedText']
				# note: tuple JIM: why?
	self.extraInfo = ( str(values[fn]) for fn in self.extraInfoFieldNames )

	return self
    #----------------------

    def getSampleAsText(self):
	""" Return this record as a text string
	"""
	fields = [ self.knownClassName,
		    self.ID,
		    self.creationDate,
		    self.year,
		    self.isReview,
		    self.refType,
		    self.suppStatus,
		    self.apStatus,
		    self.gxdStatus,
		    self.goStatus,
		    self.tumorStatus,
		    self.qtlStatus,
		    self.journal,
		    self.title,	
		    self.abstract,
		    self.extractedText,
		    ]
	return FIELDSEP.join( fields)
    #----------------------
	
    def validateClassName(self, name):
	"""
	1) validate name is a CLASS_NAME
	2) transform it as needed: remove any leading/trailing spaces and punct
	Return the cleaned up name.
	The orig need for cleaning up arose when using ';;' as the record sep
	    and having some extracted text ending in ';'.
	    So splitting records on ';;' left the record's class as ';discard'
	    which caused problems down the line.
	"""
	className_re = re.compile(r'\b(\w+)\b')	# all alpha numeric
	m = className_re.search(name)

	if m and m.group() in CLASS_NAMES:
	    return m.group()
	else:
	    raise ValueError("Invalid sample class name '%s'\n" % str(name))
    #----------------------

    def parseInput(self, s):

	values = {}
	fields = s.split(FIELDSEP)

	for i, fn in enumerate(self.fieldNames):
	    values[ fn ] = fields[i]

	return self.setFields(values)
    #----------------------

    @classmethod
    def getHeaderLine(cls):
	""" Return sample output file column header line
	"""
	return FIELDSEP.join( cls.fieldNames)

    @classmethod
    def getExtraInfoFieldNames(cls): return cls.extraInfoFieldNames
    #----------------------

    def getKnownClassName(self):return self.knownClassName
    def getKnownYvalue(self):	return CLASS_NAMES.index(self.knownClassName)
    def getJournal(self):	return self.journal
    def getExtraInfo(self):     return self.extraInfo

    #----------------------
    # "preprocessor" functions.
    #  Each preprocessor should modify this sample and return itself
    #----------------------

    def addJournalFeature(self):		# preprocessor
	''' Add the journal name as a text token to the document
	'''
	jtext = 'journal__' + '_'.join( self.journal.split(' ') ).lower()
	self.extractedText += " " + jtext
	return self
    # ---------------------------
# end class ClassifiedSample ------------------------


class UnclassifiedSample (BaseSample):
    """
    IS a sample record that we need to predict (i.e., a new, unseen article)
    Will fill this out when we get to predicting new articles
    """
    pass
# end class UnclassifiedSample ------------------------

if __name__ == "__main__":	# ad hoc test code
    r2 = ClassifiedSample().parseInput(\
    ''';discard...|pmID1|10/3/2017|1901|1|peer2|supp2|apstat2|gxdStat2|goStat2|tumorStat2|qtlStat2|journal2|title2|abstract2|text2''')
    r1 = ClassifiedSample().parseInput(\
    '''keep|pmID1|01/01/1900|1900|0|non-peer1|supp type1|apstat1|gxdstat1|goStat1|tumorstat1|qtlStat1|Journal of Insomnia|My Title|
    My Abstract|My text: it's a knock out https://foo text www.foo.org word word  -/- the final words'''
    )
    if True:	# basic Classified Sample tests
	print "----------------------"
	print "ClassifiedSample tests\n"
	print "classname: '%s'"		% r1.getKnownClassName()
	print "Y value: %d"		% r1.getKnownYvalue()
	print "SampleName: '%s'"	% r1.getSampleName()
	print "Journal: '%s'"		% r1.getJournal()
	print "title: \n'%s'\n"		% r1.getTitle()
	print "abstract: \n'%s'\n"	% r1.getAbstract()
	print "extractedText: \n'%s'\n"	% r1.getExtractedText()
	print "document: \n'%s'\n"	% r1.getDocument()
	print "Reject? %s "		% str(r1.isReject())
	print "Reason: '%s'"		% str(r1.getRejectReason())
	print "header line: \n'%s'\n" % r1.getHeaderLine()
	print "sample as text: \n'%s'\n" % r1.getSampleAsText()
	print "ExtraInfoFieldNames:\n'%s'\n" % ' '.join(r1.getExtraInfoFieldNames())
	print "ExtraInfo:" 
	for e in r1.getExtraInfo(): print e
	print

    if True: # ClassifiedSampleSet tests
	print "---------------"
	print "SampleSet tests\n"
	print r2.getKnownClassName()
	ss = ClassifiedSampleSet()
	print "header line: \n'%s'\n" % ss.getHeaderLine()
	print "Record End: \n'%s'\n" % ss.getRecordEnd()
	print "ExtraInfoFieldNames:\n'%s'\n" % ' '.join(ss.getExtraInfoFieldNames())
	ss.addSample(r1)
	ss.addSample(r2)
	print "1st sample: \n'%s'\n'" % ss.getSamples()[0].getSampleAsText()
	print "Output file:"
	ss.write(sys.stdout)
	print "\nEnd Output file"

	print
	print "Input records string" 
	e = ss.getRecordEnd()
	inputStr = ss.getHeaderLine() + e + r1.getSampleAsText() + e + r2.getSampleAsText() + e
	ss.textToSamples(inputStr)
	print "2nd sample: \n'%s'\n'" % ss.getSamples()[1].getSampleAsText()
	print "Output file:"
	ss.write(sys.stdout)
	print "\nEnd Output file"
	
    if True:		# preprocessor tests
	print "---------------"
	print "Preprocessor tests\n"
	r1.addJournalFeature()
	#r1.removeURLsCleanStem()
#	r1.removeText()
	r1.truncateText()
#	r1.tokenPerLine()
	print r1.getDocument()
