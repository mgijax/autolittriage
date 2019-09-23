#!/usr/bin/env python2.7 
#
# Library to support handling of lit triage samples (training samples or
#  samples to predict)
#
import sys
import string
import re
import utilsLib
import figureText
import featureTransform
#-----------------------------------
#
# Naming conventions:
#  * use camelCase for most things
#  * but stick to sklearn convention for y_*  which are the indexes of
#      sample classification names, e.g., 'discard', 'keep'
#  * use "class" or "classname" to mean the sample classification names
#      (e.g., so a ClassifiedSample is a sample where we know if it is
#       'discard' or 'keep')
#  * this is confusing with python "classes" and with the fact that the name
#      of a python class is passed as a config parameter to specify which
#      ClassifiedSample subclass to instantiate.
#  * so try to use "python class" or "object type" for these
#-----------------------------------

config = utilsLib.getConfig()

FIELDSEP     = eval( config.get("DEFAULT", "FIELDSEP") )
RECORDEND    = eval( config.get("DEFAULT", "RECORDEND") )
SAMPLE_OBJ_TYPE_NAME = config.get("CLASS_NAMES", "SAMPLE_OBJ_TYPE_NAME")

FIG_CONVERSION        = config.get("DEFAULT", "FIG_CONVERSION")
FIG_CONVERSION_NWORDS = config.getint("DEFAULT", "FIG_CONVERSION_NWORDS")
figConverter = figureText.Text2FigConverter(conversionType=FIG_CONVERSION,
						numWords=FIG_CONVERSION_NWORDS)
#-----------------------------------

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
    def __init__(self, sampleObjType=None):
	self.samples = []
	self.numPositives = 0
	self.numNegatives = 0
	self.journals     = set()   # set of all journal names in the samples
				   
	if sampleObjType: # The python class of sample objects
	    self.sampleObjType = sampleObjType
	else:		# get from config
	    self.sampleObjType = \
			    getattr(sys.modules[__name__], SAMPLE_OBJ_TYPE_NAME)
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
	    			# need to know which class to instantiate
	    self.addSample( self.sampleObjType().parseSampleRecordText(sr) )
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

    def addSamples(self, samples,	# samples is a [ ClassifiedSamples ]
	):
	for s in samples:
	    self.addSample(s)
	return self
    #-------------------------

    def addSample(self, sample,		# ClassifiedSample
	):
	if not isinstance(sample, self.sampleObjType):
	    raise TypeError('Invalid sample type %s' % str(type(sample)))
	self.samples.append(sample)
	if sample.isPositive(): self.numPositives += 1
	else:                   self.numNegatives += 1
	self.journals.add(sample.getJournal())
	return self
    #-------------------------

    def getSamples(self):	return self.samples
    def getNumSamples(self):	return len(self.samples)
    def getNumPositives(self):	return self.numPositives
    def getNumNegatives(self):	return self.numNegatives
    def getJournals(self):	return self.journals	# set of names
    def getRecordEnd(self):	return RECORDEND

    def getSampleObjType(self): return self.sampleObjType
    def getSampleClassNames(self):
	return self.sampleObjType.getSampleClassNames()
    def getY_positive(self):	return self.sampleObjType.getY_positive()
    def getY_negative(self):	return self.sampleObjType.getY_negative()

    def getHeaderLine(self):	return self.sampleObjType.getHeaderLine()
    def getExtraInfoFieldNames(self):
	return self.sampleObjType.getExtraInfoFieldNames()

# end class ClassifiedSampleSet -----------------------------------

#-----------------------------------
# Regex's sample preprocessors
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
	self.setExtractedText('\n\n'.join( \
			    figConverter.text2FigText(self.getExtractedText())))
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
	(?) maybe this should just break on whitespace and not tokenize
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
	self.setExtractedText(self.getExtractedText()[:20].replace('\n',' ')+'\n')
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
    Abstract class. Represents a training sample that has a known classification
	(e.g. discard/keep, selected/unselected)
    Knows how to take a text representation of a record (a text string with
	delimitted fields) and parse into its fields
    Has "extraInfoFields", information about the sample that don't necessarily
	relate to the sample features used for training/prediction, but may
	be used to subset the sample set when analyzing prediction results.
	(e.g., if we want to analyze precision/recall for individual journals)
    """
		# I think these need to be in alpha order if you
		#  load samples using sklearn's load_files() function.
		#  (and they need to match the directory names where the
		#  sample files are stored)
    sampleClassNames = ['no','yes']
    y_positive = 1	# sampleClassNames[y_positive] is the "positive" class
    y_negative = 0	# ... negative

    # fields of a sample as an input/output record (as text), in order
    # Need to be specified by subclasses
    fieldNames = [  ]
    extraInfoFieldNames = [  ] # should be [] if no extraInfoFields

    fieldSep = FIELDSEP

    def __init__(self,):
	BaseSample.__init__(self)
    #----------------------

    def parseSampleRecordText(self, text):
	"""
	Parse the text representing a sample record and populate self
	with that record
	"""
	values = {}
	fields = text.split(self.fieldSep)

	for i, fn in enumerate(self.fieldNames):
	    values[ fn ] = fields[i]

	return self.setFields(values)
    #----------------------

    def getSampleAsText(self):
	""" Return this record as a text string
	"""
	return self.fieldSep.join([ self.values[fn] for fn in self.fieldNames])
    #----------------------

    @classmethod
    def getHeaderLine(cls):
	""" Return sample output file column header line
	"""
	return cls.fieldSep.join( cls.fieldNames)
    #----------------------

    def setFields(self, values,		# dict
	):
	self.values = { fn: str(values[fn]) for fn in self.fieldNames }
	self.setKnownClassName( values['knownClassName'] )
	return self
    #----------------------

    def setKnownClassName(self, t):
	self.values['knownClassName'] = self.validateClassName(t)
	
    className_re = re.compile(r'\b(\w+)\b')	# all alpha numeric
    @classmethod
    def validateClassName(cls, className):
	"""
	1) validate className is a sampleClassName
	2) transform it as needed: remove any leading/trailing spaces and punct
	Return the cleaned up name, or raise ValueError.
	The orig need for cleaning up arose when using ';;' as the record sep
	    and having some extracted text ending in ';'.
	    So splitting records on ';;' left the record's class as ';discard'
	    which caused problems down the line.
	"""
	m = cls.className_re.search(className)

	if m and m.group() in cls.sampleClassNames:
	    return m.group()
	else:
	    raise ValueError("Invalid sample classification '%s'\n" % \
								str(className))
    #----------------------

    def getKnownClassName(self): return self.values['knownClassName']
    def getKnownYvalue(self):
	return self.sampleClassNames.index(self.getKnownClassName())
    def isPositive(self):
	return self.getKnownYvalue() == self.y_positive 
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

    def getJournal(self):  return self.values['journal']

    #----------------------
    @classmethod
    def getSampleClassNames(cls): return cls.sampleClassNames
    @classmethod
    def getY_positive(cls): return cls.y_positive
    @classmethod
    def getY_negative(cls): return cls.y_negative
    #----------------------
    @classmethod
    def getFieldSep(cls):   return cls.fieldSep
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

class PrimTriageClassifiedSample(ClassifiedSample):
    """
    Represents a training sample for primary triage that has a known
	classification (discard/keep)
    """
    sampleClassNames = ['discard','keep']
    y_positive = 1
    y_negative = 0

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
	    'abstractLen'   ,
	    'textLen'       ,
	    ]
# end class PrimTriageClassifiedSample ------------------------

class CurGroupClassifiedSample(ClassifiedSample):
    """
    Represents a training sample from a curation group that has a known
	classification (selected/unselected)
    """
    sampleClassNames = ['selected','unselected']
    y_positive = 0
    y_negative = 1

    # fields of a sample as an input/output record (as text), in order
    fieldNames = [ \
	    'knownClassName',
	    'ID'            ,
	    'creationDate'  ,
	    'year'          ,
	    'discardKeep'   ,
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
	    'discardKeep'   ,
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
# end class CurGroupClassifiedSample ------------------------


class UnclassifiedSample (BaseSample):
    """
    IS a sample record that we need to predict (i.e., a new, unseen article)
    Will fill this out when we get to predicting new articles
    """
    pass
# end class UnclassifiedSample ------------------------

if __name__ == "__main__":	# ad hoc test code
    ss = ClassifiedSampleSet(sampleObjType=PrimTriageClassifiedSample)
    print ss.getExtraInfoFieldNames()
    print ss.getSampleObjType()
    print ss.getSampleClassNames()
    print ss.getY_positive()
    print ss.getY_negative()
    if False:	# basic CurGroupClassified Sample tests
	r3 = CurGroupClassifiedSample().parseSampleRecordText(\
    '''unselected|pmID1|01/01/1900|1900|keep|0|non-peer1|supp type1|apstat1|gxdstat1|goStat1|tumorstat1|qtlStat1|Journal of Insomnia|My Title|
    My Abstract|My text: it's a knock out https://foo text www.foo.org word word  -/- the final words'''
    )
	print "----------------------"
	print "CurGroupClassifiedSample tests\n"
	print "classname: '%s'"		% r3.getKnownClassName()
	print "Y value: %d"		% r3.getKnownYvalue()
	print "Positive? %d"		% r3.isPositive()
	print "Negative? %d"		% r3.isNegative()
	print "sample as text: \n'%s'\n" % r3.getSampleAsText()
	print "ExtraInfoFieldNames:\n'%s'\n" % ' '.join(r3.getExtraInfoFieldNames())
	print "ExtraInfo:" 
	for e in r3.getExtraInfo(): print e
	print
	print "---------------"
	print "SampleSet tests\n"
	print r3.getKnownClassName()
	ss = ClassifiedSampleSet(sampleObjType=CurGroupClassifiedSample)
	print "header line: \n'%s'\n" % ss.getHeaderLine()
	print "Record End: \n'%s'\n" % ss.getRecordEnd()
	print "ExtraInfoFieldNames:\n'%s'\n" % ' '.join(ss.getExtraInfoFieldNames())
	ss.addSample(r3)
	print "1st sample: \n'%s'\n'" % ss.getSamples()[0].getSampleAsText()
	print "numPositives: %d" % ss.getNumPositives()
	print "numNegatives: %d" % ss.getNumNegatives()
	print "Journals:"
	print ss.getJournals()
    if True:	# basic PrimTriageClassified Sample tests
	r2 = PrimTriageClassifiedSample().parseSampleRecordText(\
	''';discard|pmID1|10/3/2017|1901|1|peer2|supp2|apstat2|gxdStat2|goStat2|tumorStat2|qtlStat2|journal2|title2|abstract2|text2''')
	r1 = PrimTriageClassifiedSample().parseSampleRecordText(\
	'''keep|pmID1|01/01/1900|1900|0|non-peer1|supp type1|apstat1|gxdstat1|goStat1|tumorstat1|qtlStat1|Journal of Insomnia|My Title|
	My Abstract|My text: it's a knock out https://foo text www.foo.org word word  -/- the final words'''
	)
	print "----------------------"
	print "PrimTriageClassifiedSample tests\n"
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

    if True: # ClassifiedSampleSet (for PrimTriageClassifiedSample) tests
	print "---------------"
	print "SampleSet tests\n"
	print r2.getKnownClassName()
	ss = ClassifiedSampleSet(sampleObjType=PrimTriageClassifiedSample)
	print "header line: \n'%s'\n" % ss.getHeaderLine()
	print "Record End: \n'%s'\n" % ss.getRecordEnd()
	print "ExtraInfoFieldNames:\n'%s'\n" % ' '.join(ss.getExtraInfoFieldNames())
	ss.addSample(r1)
	ss.addSample(r2)
	print "1st sample: \n'%s'\n'" % ss.getSamples()[0].getSampleAsText()
	print "numPositives: %d" % ss.getNumPositives()
	print "numNegatives: %d" % ss.getNumNegatives()
	print "Journals:"
	print ss.getJournals()
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
