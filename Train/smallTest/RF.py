import sys
import textTuningLib as tl
import sklearnHelperLib as skHelper
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import StandardScaler, MaxAbsScaler
from sklearn.ensemble import RandomForestClassifier
#-----------------------
args = tl.args
randomSeeds = tl.getRandomSeeds( { 	# None means generate a random seed
		'randForSplit'      : args.randForSplit,
		'randForClassifier' : args.randForClassifier,
		} )
pipeline = Pipeline( [
('vectorizer', CountVectorizer(
#('vectorizer', TfidfVectorizer(
		strip_accents=None,	# if done in preprocessing
		decode_error='strict',	# if handled in preproc
		lowercase=False,	# if done in preprocessing
		stop_words='english',
		binary=True,
		#token_pattern=r'\b([a-z_]\w+)\b', Use default for now
		),),
#('featureEvaluator', skHelper.FeatureDocCounter()),
#('scaler'    ,StandardScaler(copy=True,with_mean=False,with_std=True)),
#('scaler'    , MaxAbsScaler(copy=True)),
('classifier', RandomForestClassifier(verbose=1, class_weight='balanced',
		random_state=randomSeeds['randForClassifier'], n_jobs=6) ),
] )
parameters={#'vectorizer__ngram_range':[(1,2)],
	'vectorizer__min_df':[0.02],
	'vectorizer__max_df':[.75],

#	'classifier__max_features': [10],
#	'classifier__max_depth': [15],
#	'classifier__min_samples_split': [75,],
#	'classifier__min_samples_leaf': [15,],
	'classifier__n_estimators': [5],
	}
p = tl.TextPipelineTuningHelper( pipeline, parameters,
		    randomSeeds=randomSeeds,         ).fit()
print p.getReports()
