import sys
import textTuningLib as tl
import sklearnHelperLib as skHelper
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import StandardScaler, MaxAbsScaler
from sklearn.linear_model import SGDClassifier
#-----------------------
args = tl.args
randomSeeds = tl.getRandomSeeds( { 	# None means generate a random seed
		'randForSplit'      : args.randForSplit,
		'randForClassifier' : args.randForClassifier,
		} )
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
#('featureEvaluator', skHelper.FeatureDocCounter()),
('classifier', SGDClassifier(verbose=1,
			random_state=randomSeeds['randForClassifier'],
			loss='hinge', 	# = linear SVM
#			max_iter=1000,	# default in 0.20 is 5!
#			tol=0.001, 
			class_weight='balanced',
			n_jobs=-1,
		) ),
] )
parameters={
#	'classifier__alpha':[.5, ],
#	'classifier__class_weight': ['balanced'],
	'classifier__max_iter':[1000, 2000,],
	'classifier__tol':[0.001, 0.0001,],
#	'classifier__learning_rate':['optimal'],
#	'classifier__eta0':[ .01],
#	'classifier__penalty':['l2'],
	}
note='\n'.join([ "Linear SVM. max_iter=1000 instead of default 5.",
	]) + '\n'
p = tl.TextPipelineTuningHelper( pipeline, parameters, randomSeeds=randomSeeds,
		note=note,).fit()
print p.getReports()
