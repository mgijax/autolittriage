#!/usr/bin/env python3

import sys
import unittest
import os
import os.path
from sampleDataLib import *

"""
These are tests for sampleDataLib.py

Usage:   python test_sampleDataLib.py [-v]

The pattern:
    Each class in sampleDataLib.py has a corresponding *_tests class here to
    exercise methods.
"""
######################################

class PrimTriageClassifiedSample_tests(unittest.TestCase):
    def setUp(self):
        self.sample1Text = \
        '''discard|pmID1|10/3/2017|1901|1|peer reviewed|supp status1|apstat1|gxdStat1|goStat1|tumorStat1|qtlStat1|journal1|title1|abstract1|text1'''
        self.sample1 = PrimTriageClassifiedSample().parseSampleRecordText(\
                                                            self.sample1Text)
        self.sample2 = PrimTriageClassifiedSample().parseSampleRecordText(\
        '''keep|pmID2|01/01/1900|1900|0|non-peer reviewed|supp status2|apstat2|gxdstat2|goStat2|tumorstat2|qtlStat2|Journal of Insomnia|My Title w/ Fig text|
My Abstract w/ Fig text and -/-|My text: it's a knock out https://foo text www.foo.org word word  -/-.

This could be a table reference paragraph.

Figure. 1: this is a figure legend

the final words'''
        )

    def test_setgetFields(self):
        s = PrimTriageClassifiedSample()
        d = {'knownClassName': 'keep', 'ID': 'pmID4', 'extractedText': 'text',
                'foo': 'invalid field'}
        s.setFields(d)
        self.assertEqual('pmID4', s.getField('ID'))
        self.assertEqual('keep', s.getField('knownClassName'))
        self.assertEqual('text', s.getField('extractedText'))
        self.assertEqual('', s.getField('journal'))  # '' since we didn't set it
        self.assertRaises(KeyError, s.getField, 'foo')

    def test_setgetID(self):
        self.assertEqual(self.sample1.getID(), 'pmID1')
        self.sample1.setID('pmID25')
        self.assertEqual(self.sample1.getID(), 'pmID25')

    def test_getSampleName(self):
        self.assertEqual(self.sample1.getSampleName(), 'pmID1')

    def test_getSampleID(self):
        self.assertEqual(self.sample1.getSampleName(), 'pmID1')

    def test_getJournal(self):
        self.assertEqual(self.sample1.getJournal(), 'journal1')

    def test_getTitle(self):
        self.assertEqual(self.sample1.getTitle(), 'title1')

    def test_getAbstract(self):
        self.assertEqual(self.sample1.getAbstract(), 'abstract1')

    def test_getExtractedText(self):
        self.assertEqual(self.sample1.getExtractedText(), 'text1')

    def test_getDocument(self):
        doc = '\n'.join([self.sample1.getTitle(), self.sample1.getAbstract(),
                         self.sample1.getExtractedText()])
        self.assertEqual(self.sample1.getDocument(), doc)

    def test_getSampleAsText(self):
        self.assertEqual(self.sample1.getSampleAsText(), self.sample1Text)

    def test_getFieldNames(self):
        # not bothering to check for all fields, just a few
        self.assertIn('journal',   self.sample1.getFieldNames())
        self.assertIn('gxdStatus', self.sample1.getFieldNames())

    def test_getClassNames(self):
        self.assertEqual(['discard', 'keep'], self.sample1.getClassNames())

    def test_getY_positive(self):
        self.assertEqual(1, self.sample1.getY_positive())

    def test_getY_negative(self):
        self.assertEqual(0, self.sample1.getY_negative())

    def test_getHeaderLine(self):
        self.assertIn('apStatus', self.sample1.getHeaderLine())

    def test_getFieldSep(self):
        self.assertEqual('|', self.sample1.getFieldSep())

    def test_setgetKnownClassName(self):
        self.assertEqual(self.sample1.getKnownClassName(), 'discard')
        self.assertEqual(self.sample2.getKnownClassName(), 'keep')

        self.assertRaises(ValueError, self.sample1.setKnownClassName, 'bad')
        self.sample1.setKnownClassName(';discard')
        self.assertEqual(self.sample1.getKnownClassName(), 'discard')
        self.sample1.setKnownClassName(';keep')
        self.assertEqual(self.sample1.getKnownClassName(), 'keep')

    def test_getKnownYvalue(self):
        self.assertEqual(self.sample1.getKnownYvalue(), 0)
        self.assertEqual(self.sample2.getKnownYvalue(), 1)

    def test_isPositiveNegative(self):
        self.assertFalse(self.sample1.isPositive())
        self.assertTrue( self.sample1.isNegative())
        self.assertTrue( self.sample2.isPositive())
        self.assertFalse(self.sample2.isNegative())

    def test_getExtraInfo(self):
        # not bothering to check for all fields, just a few
        self.assertIn('year',     self.sample1.getExtraInfoFieldNames())
        self.assertIn('journal1', self.sample1.getExtraInfo())
        self.assertIn(str(len('abstract1')), self.sample1.getExtraInfo())

    def test_figureTextLegCloseWords50(self):
        expectedText = \
"""
My Title w/ Fig text

My Abstract w/ Fig text and -/-
This could be a table reference paragraph.

Figure. 1: this is a figure legend
""".strip()
        self.sample2.figureTextLegCloseWords50()
        self.assertEqual(expectedText, self.sample2.getDocument().strip())

    def test_removeURLsCleanStem(self):
        expectedText = \
"""
my titl figur text
 my abstract figur text and
 my text it knock_out text word word mut_mut this could be tabl refer paragraph figur this is figur legend the final word
""".strip()
        self.sample2.removeURLsCleanStem()
        self.assertEqual(expectedText, self.sample2.getDocument().strip())

# end class PrimTriageClassifiedSample_tests
######################################

class PrimTriageUnClassifiedSample_tests(unittest.TestCase):
    def setUp(self):
        self.sample1Text = '''pmID1|title1|abstract1|text1'''
        self.sample1 = PrimTriageUnClassifiedSample().parseSampleRecordText(\
                                                            self.sample1Text)
        self.sample2 = PrimTriageUnClassifiedSample().parseSampleRecordText(\
        '''pmID2|My Title w/ Fig text|
My Abstract w/ Fig text and -/-|My text: it's a knock out https://foo text www.foo.org word word  -/-.

This could be a table reference paragraph.

Figure. 1: this is a figure legend

the final words'''
        )

    def test_setgetFields(self):
        s = PrimTriageUnClassifiedSample()
        d = {'ID': 'pmID4', 'extractedText': 'text', 'foo': 'invalid field'}
        s.setFields(d)
        self.assertEqual('pmID4', s.getField('ID'))
        self.assertEqual('text', s.getField('extractedText'))
        self.assertEqual('', s.getField('abstract'))
        self.assertRaises(KeyError, s.getField, 'foo')

    def test_setgetID(self):
        self.assertEqual(self.sample1.getID(), 'pmID1')
        self.sample1.setID('pmID25')
        self.assertEqual(self.sample1.getID(), 'pmID25')

    def test_getSampleName(self):
        self.assertEqual(self.sample1.getSampleName(), 'pmID1')

    def test_getSampleID(self):
        self.assertEqual(self.sample1.getSampleName(), 'pmID1')

    def test_getTitle(self):
        self.assertEqual(self.sample1.getTitle(), 'title1')

    def test_getAbstract(self):
        self.assertEqual(self.sample1.getAbstract(), 'abstract1')

    def test_getExtractedText(self):
        self.assertEqual(self.sample1.getExtractedText(), 'text1')

    def test_getDocument(self):
        doc = '\n'.join([self.sample1.getTitle(), self.sample1.getAbstract(),
                         self.sample1.getExtractedText()])
        self.assertEqual(self.sample1.getDocument(), doc)

    def test_getSampleAsText(self):
        self.assertEqual(self.sample1.getSampleAsText(), self.sample1Text)

    def test_getFieldNames(self):
        # not bothering to check for all fields, just a few
        self.assertIn('title',         self.sample1.getFieldNames())
        self.assertIn('extractedText', self.sample1.getFieldNames())

    def test_getClassNames(self):
        self.assertEqual(['discard', 'keep'], self.sample1.getClassNames())

    def test_getY_positive(self):
        self.assertEqual(1, self.sample1.getY_positive())

    def test_getY_negative(self):
        self.assertEqual(0, self.sample1.getY_negative())

    def test_getHeaderLine(self):
        self.assertIn('abstract', self.sample1.getHeaderLine())

    def test_getFieldSep(self):
        self.assertEqual('|', self.sample1.getFieldSep())

    def test_figureTextLegCloseWords50(self):
        expectedText = \
"""
My Title w/ Fig text

My Abstract w/ Fig text and -/-
This could be a table reference paragraph.

Figure. 1: this is a figure legend
""".strip()
        self.sample2.figureTextLegCloseWords50()
        self.assertEqual(expectedText, self.sample2.getDocument().strip())

    def test_removeURLsCleanStem(self):
        expectedText = \
"""
my titl figur text
 my abstract figur text and
 my text it knock_out text word word mut_mut this could be tabl refer paragraph figur this is figur legend the final word
""".strip()
        self.sample2.removeURLsCleanStem()
        self.assertEqual(expectedText, self.sample2.getDocument().strip())

# end class PrimTriageUnClassifiedSample_tests
######################################

class SampleSet_tests(unittest.TestCase): # test PrimTriageUnclassifiedSamples
    def setUp(self):
        self.ss = SampleSet(sampleObjType=PrimTriageUnClassifiedSample)
        self.sample1Text =  '''pmID1|title1|abstract1|text1'''
        self.sample1 = PrimTriageUnClassifiedSample().parseSampleRecordText(\
                                                            self.sample1Text)
        self.sample2 = PrimTriageUnClassifiedSample().parseSampleRecordText(\
        '''pmID2|title2|abstract2|text2''')

        self.ss.addSamples([self.sample1, self.sample2]) # exercise addSamples()

    def test_addSampleTypeError(self):
        self.assertRaises(TypeError, self.ss.addSample, ClassifiedSample())

    def test_getSamples(self):
        self.assertEqual(self.sample1, self.ss.getSamples()[0])
        self.assertEqual(self.sample2, self.ss.getSamples()[1])

    def test_getSampleIDs(self):
        self.assertEqual(['pmID1', 'pmID2'], self.ss.getSampleIDs())

    def test_getDocuments(self):
        expectedDoc1 = "title1\nabstract1\ntext1"
        expectedDoc2 = "title2\nabstract2\ntext2"
        self.assertEqual(expectedDoc1, self.ss.getDocuments()[0])
        self.assertEqual(expectedDoc2, self.ss.getDocuments()[1])

    def test_getNumSamples(self):
        self.assertEqual(2, self.ss.getNumSamples())

    def test_getRecordEnd(self):
        self.assertEqual(';;', self.ss.getRecordEnd())

    def test_getSampleObjType(self):
        self.assertEqual(PrimTriageUnClassifiedSample,self.ss.getSampleObjType())

    def test_getSampleClassNames(self):
        self.assertEqual(['discard','keep'], self.ss.getSampleClassNames())

    def test_getY_positive(self):
        self.assertEqual(1, self.ss.getY_positive())

    def test_getY_negative(self):
        self.assertEqual(0, self.ss.getY_negative())

    def test_getFieldNames(self):
        # not bothering to check for all fields, just a few
        self.assertIn('abstract', self.ss.getFieldNames())
        self.assertIn('title',    self.ss.getFieldNames())

    def test_getHeaderLine(self):
        # not bothering to check for all fields, just a few
        self.assertIn('abstract', self.ss.getHeaderLine())
        self.assertIn('title',    self.ss.getHeaderLine())

    def test_write_read(self):
        fileName = 'temporarySampleOutputFile.txt'
        fp = open(fileName, 'w')
        self.ss.write(fp)
        fp.close()

        # read in the file, verify things seem identical
        fp = open(fileName, 'r')
        ss2 = SampleSet().read(fp)
        fp.close()
        self.assertEqual(self.ss.getSampleObjType(), ss2.getSampleObjType())
        self.assertEqual(self.ss.getHeaderLine(), ss2.getHeaderLine())
        self.assertEqual(self.ss.getDocuments()[0], ss2.getDocuments()[0])
        self.assertEqual(self.ss.getDocuments()[1], ss2.getDocuments()[1])

        os.remove(fileName)

    def test_rejection(self):
        # test SampleSet before rejecting any samples
        self.assertEqual(2, self.ss.getNumSamples(omitRejects=True))
        self.assertEqual([self.sample1, self.sample2],
                                self.ss.getSamples(omitRejects=True))
        self.assertEqual(['pmID1', 'pmID2'],
                                self.ss.getSampleIDs(omitRejects=True))
        expectedDoc1 = "title1\nabstract1\ntext1"
        expectedDoc2 = "title2\nabstract2\ntext2"
        self.assertEqual([expectedDoc1, expectedDoc2],
                                self.ss.getDocuments(omitRejects=True))
        # Reject one sample
        self.sample1.setReject(True, reason='my rejection reason')
        self.assertTrue(self.sample1.isReject())
        self.assertEqual('my rejection reason', self.sample1.getRejectReason())

        # test SampleSet again
        self.assertEqual(1, self.ss.getNumSamples(omitRejects=True))
        self.assertEqual([self.sample2],
                                self.ss.getSamples(omitRejects=True))
        self.assertEqual(['pmID2'],
                                self.ss.getSampleIDs(omitRejects=True))
        self.assertEqual([expectedDoc2],
                                self.ss.getDocuments(omitRejects=True))

    def test_preprocess(self):
        sample3 = PrimTriageUnClassifiedSample().parseSampleRecordText(\
        '''pmID3|My Title|
My Abstract: w/ http://url.org end abstract|
My text: https://foo text www.foo.org and text.
'''
        )
        self.ss.addSample(sample3)
        expectedText = \
"""my
title

my
abstract
w
end
abstract

my
text
text
and
text
"""
        self.ss.preprocess(['removeURLs', 'tokenPerLine'])
        self.assertEqual(expectedText, self.ss.getDocuments()[2])

# end class SampleSet_tests
######################################

class ClassifiedSampleSet_tests(unittest.TestCase):
    # test with PrimTriageClassifiedSamples
    def setUp(self):
        # build sampleSet w/ 3 samples
        self.ss = ClassifiedSampleSet(sampleObjType=PrimTriageClassifiedSample)
        self.sample1Text = \
        '''discard|pmID1|10/3/2017|1901|1|peer reviewed|supp status1|apStat1|gxdStat1|goStat1|tumorStat1|qtlStat1|journal1|title1|abstract1|text1'''
        self.sample1 = PrimTriageClassifiedSample().parseSampleRecordText(\
                                                            self.sample1Text)
        self.sample2 = PrimTriageClassifiedSample().parseSampleRecordText(\
        '''keep|pmID2|01/01/1900|1900|0|non-peer reviewed|supp status2|apStat2|gxdstat2|goStat2|tumorStat2|qtlStat2|journal2|title2|abstract2|text2'''
        )
        self.sample3 = PrimTriageClassifiedSample().parseSampleRecordText(\
        '''discard|pmID3|10/3/2017|1901|1|peer reviewed|supp status3|apStat3|gxdStat3|goStat3|tumorStat3|qtlStat3|journal3|title3|abstract3|text3''')

        self.ss.addSamples([self.sample1, self.sample2]) # exercise addSamples()
        self.ss.addSample(self.sample3)                  # exercise addSample()

    #### Methods inherited from SampleSet
    def test_addSampleTypeError(self):
        self.assertRaises(TypeError,
                            self.ss.addSample, PrimTriageUnClassifiedSample())

    def test_getSamples(self):
        self.assertEqual(self.sample1, self.ss.getSamples()[0])
        self.assertEqual(self.sample2, self.ss.getSamples()[1])
        self.assertEqual(self.sample3, self.ss.getSamples()[2])

    def test_getSampleIDs(self):
        self.assertEqual(['pmID1', 'pmID2', 'pmID3'], self.ss.getSampleIDs())

    def test_getDocuments(self):
        expectedDoc1 = "title1\nabstract1\ntext1"
        expectedDoc3 = "title3\nabstract3\ntext3"
        self.assertEqual(expectedDoc1, self.ss.getDocuments()[0])
        self.assertEqual(expectedDoc3, self.ss.getDocuments()[2])

    def test_getNumSamples(self):
        self.assertEqual(3, self.ss.getNumSamples())

    def test_getRecordEnd(self):
        self.assertEqual(';;', self.ss.getRecordEnd())

    def test_getSampleObjType(self):
        self.assertEqual(PrimTriageClassifiedSample, self.ss.getSampleObjType())

    def test_getSampleClassNames(self):
        self.assertEqual(['discard','keep'], self.ss.getSampleClassNames())

    def test_getY_positive(self):
        self.assertEqual(1, self.ss.getY_positive())

    def test_getY_negative(self):
        self.assertEqual(0, self.ss.getY_negative())

    def test_getFieldNames(self):
        # not bothering to check for all fields, just a few
        self.assertIn('abstract', self.ss.getFieldNames())
        self.assertIn('title',    self.ss.getFieldNames())

    def test_getHeaderLine(self):
        # not bothering to check for all fields, just a few
        self.assertIn('abstract', self.ss.getHeaderLine())
        self.assertIn('title',    self.ss.getHeaderLine())

    def test_write_read(self):
        fileName = 'temporarySampleOutputFile.txt'
        fp = open(fileName, 'w')
        self.ss.write(fp)
        fp.close()

        # read in the file, verify things seem identical
        fp = open(fileName, 'r')
        ss2 = ClassifiedSampleSet().read(fp)
        fp.close()
        self.assertEqual(self.ss.getSampleObjType(), ss2.getSampleObjType())
        self.assertEqual(self.ss.getHeaderLine(), ss2.getHeaderLine())
        self.assertEqual(self.ss.getDocuments()[0], ss2.getDocuments()[0])
        self.assertEqual(self.ss.getDocuments()[1], ss2.getDocuments()[1])
        self.assertEqual(self.ss.getDocuments()[2], ss2.getDocuments()[2])

        os.remove(fileName)

    def test_rejection(self):

        # test SampleSet before rejecting any samples
        self.assertEqual(3, self.ss.getNumSamples(omitRejects=True))
        self.assertEqual([self.sample1, self.sample2, self.sample3],
                                self.ss.getSamples(omitRejects=True))
        self.assertEqual(['pmID1', 'pmID2', 'pmID3'],
                                self.ss.getSampleIDs(omitRejects=True))
        self.assertEqual(['discard', 'keep', 'discard'],
                                self.ss.getKnownClassNames(omitRejects=True))
        expectedDoc1 = "title1\nabstract1\ntext1"
        expectedDoc2 = "title2\nabstract2\ntext2"
        expectedDoc3 = "title3\nabstract3\ntext3"
        self.assertEqual([expectedDoc1, expectedDoc2, expectedDoc3],
                                self.ss.getDocuments(omitRejects=True))
        # Reject one sample
        self.sample1.setReject(True, reason='my rejection reason')
        self.assertTrue(self.sample1.isReject())
        self.assertEqual('my rejection reason', self.sample1.getRejectReason())

        # test SampleSet again
        self.assertEqual(2, self.ss.getNumSamples(omitRejects=True))
        self.assertEqual([self.sample2, self.sample3],
                                self.ss.getSamples(omitRejects=True))
        self.assertEqual(['pmID2', 'pmID3'],
                                self.ss.getSampleIDs(omitRejects=True))
        self.assertEqual([expectedDoc2, expectedDoc3],
                                self.ss.getDocuments(omitRejects=True))

    def test_preprocess(self):
        sample4 = PrimTriageClassifiedSample().parseSampleRecordText(\
        '''discard|pmID4|10/3/2017|1901|1|peer reviewed|supp status4|apStat4|gxdStat4|goStat4|tumorStat4|qtlStat4|journal4|My Title|
My Abstract: w/ http://url.org end abstract|
My text: https://foo text www.foo.org and text.
'''
        )
        self.ss.addSample(sample4)
        expectedText = \
"""my
title

my
abstract
w
end
abstract

my
text
text
and
text
"""
        self.ss.preprocess(['removeURLs', 'tokenPerLine'])
        self.assertEqual(expectedText, self.ss.getDocuments()[3])

    ### Methods from ClassifiedSampleSet
    def test_getKnownClassNames(self):
        self.assertEqual(['discard', 'keep', 'discard'],
                                                self.ss.getKnownClassNames())
    def test_getKnownYvalues(self):
        self.assertEqual([0, 1, 0], self.ss.getKnownYvalues())

    def test_getNumPositives(self):
        self.assertEqual(1, self.ss.getNumPositives())

    def test_getNumNegatives(self):
        self.assertEqual(2, self.ss.getNumNegatives())

    def test_getExtraInfoFieldNames(self):
        # not bothering to check for all fields, just a few
        self.assertIn('year',     self.ss.getExtraInfoFieldNames())
        self.assertIn('apStatus', self.ss.getExtraInfoFieldNames())

# end class ClassifiedSampleSet_tests
######################################

class ClassifiedRefSampleSet_tests (unittest.TestCase):
    # test with PrimTriageClassifiedSamples
    def setUp(self):
        self.ss = ClassifiedRefSampleSet(sampleObjType=PrimTriageClassifiedSample)
        self.sample1Text = \
        '''discard|pmID1|10/3/2017|1901|1|peer reviewed|supp status1|apStat1|gxdStat1|goStat1|tumorStat1|qtlStat1|journal1|title1|abstract1|text1'''
        self.sample1 = PrimTriageClassifiedSample().parseSampleRecordText(\
                                                            self.sample1Text)
        self.sample2 = PrimTriageClassifiedSample().parseSampleRecordText(\
        '''keep|pmID2|01/01/1900|1900|0|non-peer reviewed|supp status2|apStat2|gxdstat2|goStat2|tumorStat2|qtlStat2|journal2|title2|abstract2|text2'''
        )
        self.ss.addSamples([self.sample1, self.sample2])

    def test_getJournals(self):
        self.assertEqual(set(['journal1', 'journal2']), self.ss.getJournals())

    def test_getNumSamples(self):
        self.assertEqual(2, self.ss.getNumSamples())

    def test_getNumPositives(self):
        self.assertEqual(1, self.ss.getNumPositives())

# end class ClassifiedRefSampleSet_tests
######################################

def makeSuites():           # experimenting with Suites, skip for now
    suites = [
                ('PrimTriageUnClassifiedSample',
                 PrimTriageUnClassifiedSample_tests),
                ('PrimTriageClassifiedSample',
                 PrimTriageClassifiedSample_tests),
             ]
    return suites

if __name__ == '__main__':
    if True: unittest.main()
    else:           # experimenting with Suites, skip for now
        suites = makeSuites()
        runner = unittest.TextTestRunner(verbosity=1)
        for t, s in suites:
            sys.stderr.write('------------------------------\n')
            sys.stderr.write('%s tests:\n' % t)
            suite = unittest.TestSuite()
            suite.addTest(unittest.makeSuite(s))
            runner.run(suite)
