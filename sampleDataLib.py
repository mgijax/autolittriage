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
Y_POSITIVE   = cp.getint("CLASS_NAMES", "y_positive")

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
	self.numPositives = 0
	self.numNegatives = 0
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

	for sr in rcds:
	    self.addSample( ClassifiedSample().parseSampleRecordText(sr) )
	return self
    #-------------------------

    def write(self, outFile,	# file pathname or open file obj for writing
	writeHeader=True,
	omitRejects=False,
	):
	if type(outFile) == type(''): fp = open(outFile, 'w')
	else: fp = outFile

	if writeHeader:  fp.write(self.getHeaderLine() + RECORDEND)

	for s in self.sampleIterator(omitRejects=omitRejects):
	    fp.write(s.getSampleAsText() + RECORDEND)
	return self
    #-------------------------

    def sampleIterator(self,
	omitRejects=False,
	):
	for s in self.samples:
	    if omitRejects and s.isReject(): continue
	    yield s
    #-------------------------

    def addSamples(self, samples,	# [ ClassifiedSamples ]
	):
	for s in samples:
	    self.addSample(s)
	return self
    #-------------------------

    def addSample(self, sample,		# ClassifiedSample
	):
	if not isinstance(sample, ClassifiedSample):
	    raise TypeError('Invalid sample type %s' % str(type(sample)))
	self.samples.append(sample)
	if sample.isPositive(): self.numPositives += 1
	else:                   self.numNegatives += 1
	return self
    #-------------------------

    def getSamples(self):	return self.samples
    def getNumSamples(self):	return len(self.samples)
    def getNumPositives(self):	return self.numPositives
    def getNumNegatives(self):	return self.numNegatives
    def getRecordEnd(self):	return RECORDEND
    def getHeaderLine(self):	return ClassifiedSample.getHeaderLine()
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
    JIM: think about refactoring this class into a (real) BaseSample that lives
	in MLtextTools and BaseArticleSample that lives in sampleDataLib.
	Then (Un)ClassifiedSample would inherit from BaseArticleSample
    """
    def __init__(self,):
	pass
    #----------------------

    def constructDoc(self):
	return '\n'.join([self.getTitle(), self.getAbstract(),
							self.getExtractedText()])

    #----------------------
    def getSampleName(self):	return self.getID()
    def getSampleID(self):	return self.getID()
    def getName(self):		return self.getID()

    def getDocument(self):	return self.constructDoc()
    #----------------------

    #----------------------
    # "preprocessor" functions.
    #  Each preprocessor should modify this sample and return itself
    #----------------------

    def figureText(self):		# preprocessor
	self.setExtractedText( '\n'.join( \
			    figConverter.text2FigText(self.getExtractedText()) ) )
	return self
    # ---------------------------

    def featureTransform(self):		# preprocessor
	self.setTitle( featureTransform.transformText(self.getTitle()) )
	self.setAbstract( featureTransform.transformText(self.getAbstract()) )
	self.setExtractedText( featureTransform.transformText( \
						self.getExtractedText()) )
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

	self.setTitle( _removeURLsCleanStem( self.getTitle()) )
	self.setAbstract( _removeURLsCleanStem( self.getAbstract()) )
	self.setExtractedText( _removeURLsCleanStem( self.getExtractedText()) )
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
	self.setTitle( _removeURLs( self.getTitle()) )
	self.setAbstract( _removeURLs( self.getAbstract() ) )
	self.setExtractedText( _removeURLs( self.getExtractedText() ) )
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
	self.setTitle( _tokenPerLine( self.getTitle()) )
	self.setAbstract( _tokenPerLine( self.getAbstract()) )
	self.setExtractedText( _tokenPerLine( self.getExtractedText()) )
	return self
    # ---------------------------

    def truncateText(self):		# preprocessor
	""" for debugging, so you can see a sample record easily"""
	
	self.setTitle( self.getTitle()[:10].replace('\n',' ') )
	self.setAbstract( self.getAbstract()[:20].replace('\n',' ') )
	self.setExtractedText( self.getExtractedText()[:20].replace('\n',' ')+'\n' )
	return self
    # ---------------------------

    def removeText(self):		# preprocessor
	""" for debugging, so you can see a sample record easily"""
	
	self.setTitle( self.getTitle()[:10].replace('\n',' ') )
	self.setAbstract( 'abstract...' )
	self.setExtractedText( 'extracted text...\n' )
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
    				# should be [] if no extraInfoFields
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
	    'abstractLen'   ,
	    'textLen'       ,
	    ]

    def __init__(self,):
	super(type(self), self).__init__()
    #----------------------

    def parseSampleRecordText(self, text):
	"""
	Parse the text representing a sample record and populate self
	with that record
	"""
	values = {}
	fields = text.split(FIELDSEP)

	for i, fn in enumerate(self.fieldNames):
	    values[ fn ] = fields[i]

	return self.setFields(values)
    #----------------------

    def getSampleAsText(self):
	""" Return this record as a text string
	"""
	return FIELDSEP.join( [ self.values[fn] for fn in self.fieldNames ] )
    #----------------------

    @classmethod
    def getHeaderLine(cls):
	""" Return sample output file column header line
	"""
	return FIELDSEP.join( cls.fieldNames)
    #----------------------

    def setFields(self, values,		# dict
	):
	self.values = { fn: str(values[fn]) for fn in self.fieldNames }
	self.setKnownClassName( values['knownClassName'] )
	return self
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

    def setKnownClassName(self, t):
	self.values['knownClassName'] = self.validateClassName(t)

    def getKnownClassName(self): return self.values['knownClassName']
    def getKnownYvalue(self):    return CLASS_NAMES.index(self.getKnownClassName())
    def isPositive(self):
	return CLASS_NAMES.index(self.getKnownClassName()) == Y_POSITIVE 
    def isNegative(self):
	return not self.isPositive()

    def setID(self, t): self.values['ID'] = t
    def getID(self,  ): return self.values['ID']

    def setExtractedText(self, t): self.values['extractedText'] = t
    def getExtractedText(self,  ): return self.values['extractedText']

    def setAbstract(self, t): self.values['abstract'] = t
    def getAbstract(self,  ): return self.values['abstract']

    def setTitle(self, t): self.values['title'] = t
    def getTitle(self,  ): return self.values['title']

    def getJournal(self):	return self.values['journal']

    #----------------------
    @classmethod
    def getExtraInfoFieldNames(cls): return cls.extraInfoFieldNames
    def getExtraInfo(self):
	self.extraInfo = { fn : str(self.values.get(fn,'none')) \
					for fn in self.getExtraInfoFieldNames() }
	self.setComputedExtraInfoFields()
	return [ self.extraInfo[x] for x in self.getExtraInfoFieldNames() ]
	
    def setComputedExtraInfoFields(self):
	self.extraInfo['abstractLen'] = str( len(self.getAbstract()) )
	self.extraInfo['textLen']     = str( len(self.getExtractedText()) )
    #----------------------

    # preprocessSamples.py script checks for rejected samples.
    #  For autolittriage, we don't have any checks to reject samples (yet)
    def isReject(self):		return False
    def getRejectReason(self):	return None

    #----------------------
    # "preprocessor" functions.
    #  Each preprocessor should modify this sample and return itself
    #----------------------

    def addJournalFeature(self):		# preprocessor
	''' Add the journal name as a text token to the document
	'''
	jtext = 'journal__' + '_'.join( self.getJournal().split(' ') ).lower()
	self.setExtractedText( self.getExtractedText() + " " + jtext )
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
    r2 = ClassifiedSample().parseSampleRecordText(\
    ''';discard...|pmID1|10/3/2017|1901|1|peer2|supp2|apstat2|gxdStat2|goStat2|tumorStat2|qtlStat2|journal2|title2|abstract2|text2''')
    r1 = ClassifiedSample().parseSampleRecordText(\
    '''keep|pmID1|01/01/1900|1900|0|non-peer1|supp type1|apstat1|gxdstat1|goStat1|tumorstat1|qtlStat1|Journal of Insomnia|My Title|
    My Abstract|My text: it's a knock out https://foo text www.foo.org word word  -/- the final words'''
    )
    if True:	# basic Classified Sample tests
	print "----------------------"
	print "ClassifiedSample tests\n"
	print "classname: '%s'"		% r1.getKnownClassName()
	print "Y value: %d"		% r1.getKnownYvalue()
	print "Positive? %d"		% r1.isPositive()
	print "Negative? %d"		% r1.isNegative()
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
	print "numPositives: %d" % ss.getNumPositives()
	print "numNegatives: %d" % ss.getNumNegatives()
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
	
    if False:		# preprocessor tests
	print "---------------"
	print "Preprocessor tests\n"
	r1.addJournalFeature()
	#r1.removeURLsCleanStem()
#	r1.removeText()
	r1.truncateText()
#	r1.tokenPerLine()
	print r1.getDocument()
