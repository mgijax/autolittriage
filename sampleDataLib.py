#!/usr/bin/env python3
#
# Library to support handling of lit triage samples (training samples or
#  samples to predict)
#
# There are automated unit tests for this module:
#   cd test
#   python test_sampleDataLib.py -v
#
import sys
import os.path
import string
import re
from copy import copy
from baseSampleDataLib import *
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
Class_Hierarchy_Overview = \
"""
In baseSampleDataLib.py (MLTextTools)
    BaseSample
        - a text sample (classified or not) for a binary ML problem.
        - knows the two class names for the problem (e.g., "no", "yes"),
            their Y values (0/1), & which is considered the "positive" class.
        - has an arbitrary list of fields
            "ID" must be one of these
            "text" is a field by default. Can be overridden in subclasses.
        - getDocument() returns the text to be consider by a classifier
            (the "text" field by default, but subclasses may combine multiple
             fields into the "document", e.g., title, abstract, extractedText)
        - a sample may be "rejected" and have a rejection reason. Idea:
            During preprocessing, we may decide that a sample is not suitable
            for training or classification
            (relevanceClassifier doesn't use this feature)
        - implements converting a Sample to and from text for reading/writing
        - Samples can have preprocessing methods that modify the state of 
            the sample (e.g., stemming the text)
        - BaseSample implements some generic preprocessing primitives
    ClassifiedSample
        - a text sample that is classified (has a knownClassName, Y value)
        - has an optional set of ExtraInfo fields: additional info about the
            sample that is not meant to be used by a classifier but is useful
            for analyzing classifier results
    SampleSet
        - a collection of Samples of the same type (BaseSample or descendent)
        - reads/writes Sample files incl. optional meta data
        - get parallel lists:    getSamples(), getSampleIDs(), getDocuments() 
    ClassifiedSampleSet
        - a SampleSet of ClassifiedSamples
        - get parallel lists:    getKnownClassNames(), getKnownYvalues()
        - getExtraInfoFieldNames()
    SampleSetMetaData
        - info about the Samples in a Sample file
        - most important: name of the SampleObjType (python class name)
            & the name of the python module that defines that type
                (new in Jan 2021, previous versions assumed "sampleDataLib")
        - enables SampleSet to read/write sets of different types of Samples
        - meta data in a sample file is still optional for backward
            compatability, but it would be simpler to make it required at this
            point

In sampleDataLib.py (autolittriage)
    RefSample
        - a BaseSample that represents a reference
        - has fields: title, abstract, extractedText (instead of 'text')
        - implements preprocessing methods relevant for references, e.g.,
            finding figure text, feature transforms
    ClassifiedRefSample
        - a RefSample that is also a ClassifiedSample
        - includes a journal field since this is important for triage analysis
            (journal could probably just become an extraInfoField at this point,
            but historically, we considered (and rejected) restricting training
            samples to certain journals and using journal name as a feature)
    PrimTriageClassifiedSample
        - a ClassifiedRefSample for the relevance classifier
        - has class names "discard" and "keep"
        - has all the extraInfoFields used to analyze the relevance classifier
            prediction results
    PrimTriageUnClassifiedSample
        - a RefSample for the relevance classifier
        - has class names "discard" and "keep"
        - has fields:  ID, title, abstract, extractedText

    ClassifiedRefSampleSet
        - a ClassifiedSampleSet of ClassifiedRefSamples
        - has the set of journals that all the references are from

    CurGroupClassifiedSample    - JUST EXPERIMENTAL
        - a ClassifiedRefSample for the secondary triage classification
        - has class names "selected" and "unselected"
    CurGroupUnClassifiedSample  - JUST EXPERIMENTAL
        - a RefSample for secondary triage classification
        - has class names "selected" and "unselected"
"""

FIELDSEP     = '|'      # field separator when reading/writing sample fields
RECORDEND    = ';;'     # record ending str when reading/writing sample files

figConverterLegends      = figureText.Text2FigConverter( \
                                            conversionType='legends')
figConverterLegParagraphs   = figureText.Text2FigConverter( \
                                            conversionType='legParagraphs')
figConverterLegCloseWords50 = figureText.Text2FigConverter( \
                                            conversionType='legCloseWords',
                                            numWords=50)
#-----------------------------------
# Regex's sample preprocessors
urls_re      = re.compile(r'\b(?:https?://|www[.]|doi)\S*',re.IGNORECASE)
token_re     = re.compile(r'\b([a-z_]\w+)\b',re.IGNORECASE)

stemmer = None		# see preprocessor below
#-----------------------------------

class RefSample (BaseSample):
    """
    Represents a reference sample (article) that may be classified or not.

    HAS: ID, title, abstract, extracted text

    Provides various methods to preprocess a sample record
    (preprocess the text prior to vectorization)
    """
    sampleClassNames = ['no','yes']
    y_positive = 1	# sampleClassNames[y_positive] is the "positive" class
    y_negative = 0	# ... negative

    # fields of a sample as an input/output record (as text), in order
    fieldNames = [ \
            'ID'            ,
            'title'         ,
            'abstract'      ,
            'extractedText' ,
            ]
    fieldSep = FIELDSEP
    #----------------------

    def constructDoc(self):
        return '\n'.join([self.getTitle(), self.getAbstract(),
                                                    self.getExtractedText()])

    def setExtractedText(self, t): self.values['extractedText'] = t
    def getExtractedText(self,  ): return self.values['extractedText']

    def setAbstract(self, t): self.values['abstract'] = t
    def getAbstract(self,  ): return self.values['abstract']

    def setTitle(self, t): self.values['title'] = t
    def getTitle(self,  ): return self.values['title']

    #----------------------
    # "preprocessor" functions.
    #  Each preprocessor should modify this sample and return itself
    #----------------------

    def figureTextLegends(self):	# preprocessor
        # just figure legends
        self.setExtractedText('\n\n'.join( \
                figConverterLegends.text2FigText(self.getExtractedText())))
        return self
    # ---------------------------

    def figureTextLegParagraphs(self):	# preprocessor
        # figure legends + paragraphs discussing figures
        self.setExtractedText('\n\n'.join( \
            figConverterLegParagraphs.text2FigText(self.getExtractedText())))
        return self
    # ---------------------------

    def figureTextLegCloseWords50(self):	# preprocessor
        # figure legends + 50 words around "figure" references in paragraphs
        self.setExtractedText('\n\n'.join( \
            figConverterLegCloseWords50.text2FigText(self.getExtractedText())))
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
        # By importing here, we can use RefSample in situations where we don't
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
        self.setTitle( utilsLib.removeURLsLower( self.getTitle()) )
        self.setAbstract( utilsLib.removeURLsLower( self.getAbstract() ) )
        self.setExtractedText(utilsLib.removeURLsLower(self.getExtractedText()))
        return self
    # ---------------------------

    def tokenPerLine(self):		# preprocessor
        """
        Convert text to have one alphanumeric token per line,
            removing punctuation.
        Makes it easier to examine the tokens/features
        """
        self.setTitle( utilsLib.tokenPerLine( self.getTitle()) )
        self.setAbstract( utilsLib.tokenPerLine( self.getAbstract()) )
        self.setExtractedText( utilsLib.tokenPerLine( self.getExtractedText()) )
        return self
    # ---------------------------

    def truncateText(self):		# preprocessor
        """ for debugging, so you can see a sample record easily"""
        
        self.setTitle( self.getTitle()[:10].replace('\n',' ') )
        self.setAbstract( self.getAbstract()[:20].replace('\n',' ') )
        self.setExtractedText(self.getExtractedText()[:20].replace('\n',' ') \
                                                                        +'\n')
        return self
    # ---------------------------

    def removeText(self):		# preprocessor
        """ for debugging, so you can see a sample record easily"""
        
        self.setTitle( self.getTitle()[:10].replace('\n',' ') )
        self.setAbstract( 'abstract...' )
        self.setExtractedText( 'extracted text...\n' )
        return self
    # ---------------------------

    def replaceText(self):		# preprocessor
        """ for debugging, replace the extracted text with text from a file
            Filename is <ID>.new.txt
        """
        fileName = self.getID() + ".new.txt"
        if os.path.isfile(fileName):
            newText = open(fileName, 'r').read()
            self.setExtractedText(newText)
        return self
    # ---------------------------
# end class RefSample ------------------------

class ClassifiedRefSample (RefSample, ClassifiedSample):
    """
    A reference Sample (article) that is classified and has a journal field.
    """
    fieldNames = [ \
            'knownClassName',
            'ID'            ,
            'journal'       ,
            'title'         ,
            'abstract'      ,
            'extractedText' ,
            ]
    extraInfoFieldNames = [  ] # should be [] if no extraInfoFields
    #----------------------

    def setFields(self, values,		# dict
        ):
        ClassifiedSample.setFields(self, values)
        return self

    def constructDoc(self):
        return RefSample.constructDoc(self)
        
    def getJournal(self):  return self.values['journal']

    def setComputedExtraInfoFields(self):
        self.extraInfo['abstractLen'] = str( len(self.getAbstract()) )
        self.extraInfo['textLen']     = str( len(self.getExtractedText()) )
    #----------------------
# end class ClassifiedRefSample ------------------------

class PrimTriageClassifiedSample(ClassifiedRefSample):
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

class PrimTriageUnClassifiedSample(RefSample):
    """
    Represents a sample document to predict for primary triage
    """
    sampleClassNames = ['discard','keep']
    y_positive = 1
    y_negative = 0

    # fields of a sample as an input/output record (as text), in order
    fieldNames = [ \
            'ID'            ,
            'title'         ,
            'abstract'      ,
            'extractedText' ,
            ]
# end class PrimTriageUnClassifiedSample ------------------------

class ClassifiedRefSampleSet (ClassifiedSampleSet):
    """
    IS:     a ClassifiedSampleSet of (classified) reference Samples
    HAS:    set of journals from the samples
    """
    def __init__(self, sampleObjType=None):
        super().__init__(sampleObjType=sampleObjType)
        self.journals     = set()   # set of all journal names in the samples
    #-------------------------

    def addSample(self, sample,		# ClassifiedSample w/ a journal field
        ):
        super().addSample(sample)
        self.journals.add(sample.getJournal())
        return self
    #-------------------------

    def getJournals(self):	return self.journals	# set of names
# end class ClassifiedRefSampleSet -----------------------------------



class CurGroupClassifiedSample(ClassifiedRefSample):
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

class CurGroupUnClassifiedSample(RefSample):
    """
    Represents a sample document to predict
    """
    sampleClassNames = ['selected','unselected']
    y_positive = 0
    y_negative = 1

    # fields of a sample as an input/output record (as text), in order
    fieldNames = [ \
            'ID'            ,
            'title'         ,
            'abstract'      ,
            'extractedText' ,
            ]
# end class CurGroupUnClassifiedSample ------------------------

if __name__ == "__main__":
    pass
