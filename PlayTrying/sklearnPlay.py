#!/usr/bin/env python3

"""
    play with vectorizers, classifiers, etc.
"""

import sys
import time
import re
import string
import os
import os.path
import argparse
import configparser

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
from sklearn.ensemble import RandomForestClassifier
import textTuningLib as ttl


# understand output of load_files
if False:
    ds = load_files('/Users/jak/work/autolittriage/Data/smallset')
    print(list(ds.keys()))
    print(ds.target_names)
    print(len(ds.data))
    print(len(ds.target))
    print(len(ds.filenames))
    print()

# Playing with vectorizer params. When does min_df vs ngrams, etc. happen
if False:
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

    print(type(x_train))

    print(vect.get_feature_names())
    print(x_train.toarray())

# try vectorizing full documents
if False:
    startTime = time.time()

    path = '/Users/jak/work/autolittriage/Data/jan2/trainSetFig.txt'
    print(path)

    ds = ttl.DocumentSet()
    ds.load(path)

    loadTime = time.time()
    print("load time: %8.3f seconds" % loadTime - startTime)

    vect = CountVectorizer( \
                            min_df=0.02,
                            max_df=0.75,
                            stop_words="english",
                            ngram_range=(1,2),
                            binary=True,
                            )
    docs = ds.getDocs()
    print("Documents: %d" % len(ds.getDocs()))
    vect.fit(docs)

    fitTime = time.time()
    print("fit time: %8.3f seconds" % fitTime - loadTime)

    x_train = vect.transform(docs)
    print(type(x_train))

    transformTime = time.time()
    print("transform time: %8.3f seconds" % transformTime - fitTime)

    print("num features: %d" % len(vect.get_feature_names()))

    print(ttl.getVectorizerReport(vect))
    print("total time: %8.3f seconds" % time.time() - startTime)

# Playing with RandomForest params.
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
                            ngram_range=(1,1),
                            )
    vect.fit(docs)

    x_train = vect.transform(docs)

    rf = RandomForestClassifier()

    rf.fit(x_train, [1,0,1,0])

    selCoef = lambda x: x[1]
    pairList = list(zip(vect.get_feature_names(), rf.feature_importances_))

    print(sorted(pairList, key=selCoef, reverse=True))

