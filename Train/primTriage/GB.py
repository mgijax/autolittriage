import sys
import textTuningLib as tl
import sklearnHelperLib as skHelper
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
#		n_jobs=2,
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
#('featureEvaluator', skHelper.FeatureDocCounter()),
('classifier', GradientBoostingClassifier(verbose=1, 
		random_state=randomSeeds['randForClassifier'],
		#init=RFclassifier,
		learning_rate=0.05,
		n_estimators=1600,
		max_depth=3,
		min_samples_split=600,
		min_samples_leaf=150,
		max_features=0.7,
		subsample=0.85,
		) ),
] )
parameters={
#	'classifier__init':   [RFclassifier],
#	'classifier__learning_rate': [0.025],
#	'classifier__n_estimators': [3200,],
#	'classifier__max_depth': [3, 6, 9 ],
#	'classifier__min_samples_split': [525, 550, 575, 600, 625, ],
#	'classifier__min_samples_leaf': [100, 125, 150, 175],
#	'classifier__max_features': [0.6, 0.65, 0.7, 0.75, 0.8, 0.9, None, ],
#	'classifier__subsample': [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0,],
	}
note='\n'.join([ "blessed GB.",
	 ]) + '\n'
p = tl.TextPipelineTuningHelper( pipeline, parameters, randomSeeds=randomSeeds,
		note=note,).fit()
print(p.getReports())
