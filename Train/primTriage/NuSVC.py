import sys
import textTuningLib as tl
import sklearnHelperLib as skHelper
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import StandardScaler, MaxAbsScaler
#from sklearn.linear_model import SGDClassifier
import sklearn.svm as svm
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
('classifier', svm.NuSVC(verbose=True,
                        random_state=randomSeeds['randForClassifier'],
                        kernel='rbf',
                        gamma='scale',	# default for 0.22
                        #class_weight='balanced',
                ) ),
] )
parameters={
#	'classifier__alpha':[.5, ],
#	'classifier__class_weight': ['balanced'],
#	'classifier__max_iter':[1000, 2000,],
#	'classifier__tol':[0.001, 0.0001,],
#	'classifier__learning_rate':['optimal'],
#	'classifier__eta0':[ .01],
#	'classifier__penalty':['l2'],
        }
note='\n'.join([ "NuSVC. Mostly using defaults.",
        ]) + '\n'
p = tl.TextPipelineTuningHelper( pipeline, parameters, randomSeeds=randomSeeds,
                note=note,).fit()
print(p.getReports())
