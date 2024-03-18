#!/bin/bash

#
# http://bhmgiwk01lp.jax.org/mediawiki/index.php/sw:Autolittriage
# Retraining Lite
# 

PYTHON=${ANACONDAPYTHON}; export PYTHON
PYTHONPATH=${PYTHONPATH}:${ANACONDAPYTHONLIB}; export PYTHONPATH
MLBIN=/usr/local/mgi/live/lib/python_anaconda; export MLDIN
DATA=/data/relevanceClassifier/nov2020/LegendsWords/Proc1; export DATA

echo $PYTHON
echo $PYTHONPATH
echo $MLBIN
echo $DATA

ls -l $DATA

# cd to /data/relevanceClassifier directry
# make copy of existing pkl file
cd /data/relevanceClassifier
rm -rf relevanceClassifier.pkl.bak
cp -r relevanceClassifier.pkl relevanceClassifier.pkl.bak
ls -l /data/relevanceClassifier

$ANACONDAPYTHON $MLBIN/trainModel.py -m $MLBIN/relevanceClassifier.py -o relevanceClassifier.pkl -f relevanceClassifier.features $DATA/trainSet.txt $DATA/valSet.txt $DATA/testSet.txt

# run a test

#$ANACONDAPYTHON $MLBIN/predict.py -m relevanceClassifier.pkl --performance test_2020.summary -p figureTextLegCloseWords50 -p removeURLsCleanStem /data/relevanceClassifier/nov2020/test_2020 > test_2020.preds.txt

