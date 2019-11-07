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
# Create RF classifier for the initial step of the GB
import numpy as np
from sklearn.ensemble import RandomForestClassifier

class Working_Init_Classifier:
    # this gets around init param bug in GB classifer in sklearn 0.20.3 & 4
    def __init__(self, estimator):
        self.estimator = estimator
    def predict(self, X):
        return self.estimator.predict_proba(X)[:, 1][:, np.newaxis]
    def fit(self, X, y,sample_weight=None, **fit_params):
        self.estimator.fit(X, y)

RFclassifier = Working_Init_Classifier(RandomForestClassifier(verbose=0,
                class_weight='balanced',
                random_state=randomSeeds['randForClassifier'],
                n_estimators=50,
                min_samples_leaf=15,
                ))
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
('classifier', GradientBoostingClassifier(verbose=1, 
		random_state=randomSeeds['randForClassifier'],
		init=RFclassifier,
		) ),
] )
parameters={
	'classifier__learning_rate': [1.0],	# fix this for now
	'classifier__n_estimators': [80,],	# fix this for now
	'classifier__max_depth': [3, 6, 9 ],
	'classifier__min_samples_split': [500, 750, 1000,],
	'classifier__min_samples_leaf': [200,],
	'classifier__max_features': ['sqrt'],
	'classifier__subsample': [0.8],
#	'classifier__init':   [RFclassifier],
	}
note='\n'.join([ "Using initial learning_rate: 1.0, estimators: 80.",
	    "Looking for max_depth and min_samples_split.",
	    "init param: RF n_estimators=50, min_samples_leaf=15",
	 ]) + '\n'
p = tl.TextPipelineTuningHelper( pipeline, parameters, randomSeeds=randomSeeds,
		note=note,).fit()
print(p.getReports())
