import sys
import textTuningLib as tl
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import StandardScaler, MaxAbsScaler
#from sklearn.linear_model import SGDClassifier
from sklearn.ensemble import GradientBoostingClassifier
#-----------------------

args = tl.args
randomSeeds = tl.getRandomSeeds( { 	# None means generate a random seed
		'randForSplit'      : args.randForSplit,
		'randForClassifier' : args.randForClassifier,
		} )

#-----------------------
import numpy as np
from sklearn.ensemble import RandomForestClassifier

class Working_Init_Classifier:
    def __init__(self, estimator):
        self.estimator = estimator
    def predict(self, X):
        return self.estimator.predict_proba(X)[:, 1][:, np.newaxis]
    def fit(self, X, y,sample_weight=None, **fit_params):
        self.estimator.fit(X, y)

RFclassifier = Working_Init_Classifier(RandomForestClassifier(verbose=1,
		class_weight='balanced',
		random_state=randomSeeds['randForClassifier'],
		n_estimators=5,
		min_samples_split=75,
		)
		)
#-----------------------
pipeline = Pipeline( [
('vectorizer', CountVectorizer(
#('vectorizer', TfidfVectorizer(
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
#('featureEvaluator', skHelper.FeatureDocCounter()),
#('scaler'    ,StandardScaler(copy=True,with_mean=False,with_std=True)),
#('scaler'    , MaxAbsScaler(copy=True)),
('classifier', GradientBoostingClassifier(verbose=1, 
		random_state=randomSeeds['randForClassifier'],
		init=RFclassifier,
		) ),
] )
parameters={
	'vectorizer__ngram_range':[(1,1)],
	'vectorizer__min_df':[0.01, 0.02],
	'vectorizer__max_df':[.75],

#	'classifier__max_features': [10],
	'classifier__max_depth': [3, 5, 8],
#	'classifier__min_samples_split': [75,],
#	'classifier__min_samples_leaf': [25,],
	'classifier__n_estimators': [20, 25],
	}
p = tl.TextPipelineTuningHelper( pipeline, parameters,
		    randomSeeds=randomSeeds,).fit()
print p.getReports()
