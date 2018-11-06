#!/usr/bin/env python2.7

"""
    play with vectorizers
"""

import sys
import time
import re
import string
import os
import os.path
import argparse
import ConfigParser

import sklearnHelperLib as skhelper

import numpy as np
from sklearn.datasets import load_files
from sklearn.pipeline import Pipeline
#from sklearn.model_selection import train_test_split
#from sklearn.model_selection import GridSearchCV
#from sklearn.metrics import make_scorer, fbeta_score, precision_score,\
#                        recall_score, classification_report, confusion_matrix
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import StandardScaler, MaxAbsScaler
from sklearn.linear_model import SGDClassifier


# understand output of load_files
if False:
    ds = load_files('/Users/jak/work/autolittriage/Data/smallset')
    print ds.keys()
    print ds.target_names
    print len(ds.data)
    print len(ds.target)
    print len(ds.filenames)
    print

# Playing with vectorizer params. When does min_df vs ngrams, etc. happen
if True:
    docs = [
	"let them eat cake",
	"I like cake too and eat cake.",
	"you can't have your cake and eat it too",
	"that was a piece of cake!",
	]

    vect = CountVectorizer( \
			    min_df=2,
			    #stop_words="english",
			    ngram_range=(1,2),
			    )
    vect.fit(docs)

    x_train = vect.transform(docs)

    print type(x_train)

    print vect.get_feature_names()
    print x_train.toarray()
