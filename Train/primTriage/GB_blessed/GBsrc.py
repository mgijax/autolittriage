#
# Good classifier for primTriage.
# Gradient Boosting Classifier from December 2019
#import sys
#import textTuningLib as tl
#import sklearnHelperLib as skHelper
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer
#from sklearn.preprocessing import StandardScaler, MaxAbsScaler
from sklearn.ensemble import GradientBoostingClassifier
#import numpy as np

#-----------------------

pipeline = Pipeline( [
('vectorizer', CountVectorizer(
		strip_accents=None,	# if done in preprocessing
		decode_error='strict',	# if handled in preproc
		lowercase=False,	# if done in preprocessing
		stop_words='english',
		binary=True,
		#token_pattern=r'\b([a-z_]\w+)\b', Use default for now
		ngram_range=(1,2),
		min_df=0.02,
		max_df=.75,
		),),
('classifier', GradientBoostingClassifier(verbose=1, 
		#random_state=randomSeeds['randForClassifier'],
		learning_rate=0.05,
		n_estimators=1600,
		max_depth=3,
		min_samples_split=600,
		min_samples_leaf=150,
		max_features=0.7,
		subsample=0.85,
		) ),
] )
