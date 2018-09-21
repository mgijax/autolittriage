#!/usr/bin/python2.7

"""
    Name: nerLib.py
	NER: Named-Entity Recognition Module
    Author:  Jim, Sept 2018
    
    Purpose:
    Provides classes for doing named entity recognition, i.e., the task of
    finding the names of specific entities, e.g., "Pax6" or
    "Huntington disease" and mapping them to their general class/concept,
    e.g., "gene" and "disease" respectively.
    This can greatly reduce the number of distinct terms in documents to
    analyze and remove distinctions that seem irrelevant to the document
    relevance task at hand.

    This module provides a base class for NER tools and specific classes
    for implementing or using an external NER tool.

    Nomenclature:
    "entity" is a specific "thing" that belongs to some category
	e.g., the Pax6 gene in the mouse genome
    "entity name" is a specific piece of text that names an entity
	e.g., "Pax6" and all the synonyms of Pax6
    "concept" is the general category of a collection of entities,
    	e.g., "gene" or "disease" or "anatomy term", ...
    "nerText" is a piece of text with its entity names replaced by their concept
	names.

    In general, NER is concerned with mapping entity names to both their
	entities (i.e., "Pax6" and its synonyms to the Pax6 MGI ID) and to
	their concepts (gene).
    BUT we are only concerned with the mapping to concepts so we can
	replace "Pax6", "Kit", etc. with "gene_name" 

    In the code below, we will generally not distinguish between entities and
	entity names.
"""

import sys
import os
import time
import json
#import simpleURLLib as surl
#import NCBIutilsLib as eulib
#import xml.etree.ElementTree as ET
#import runCommand
#import Dispatcher
# --------------------------
# Constants
# --------------------------

# Constants for naming concepts. We are interested in certain concepts.
# The values of these constants are what the entity name in text gets
# replaced with when we convert the entity names by their concept names.
diseaseConcept     = "disease_name"
geneProteinConcept = "gene_protein_name" # gene/protein, hard to distinguish
anatomyConcept     = "anatomy_name"

# dict of which concepts to do NER for. True means do it. False means skip
# (some NER tools only support subsets of these concepts)
allConcepts = { diseaseConcept :    True,
		geneProteinConcept: True,
		anatomyConcept:     True,
	    }
# more...

# --------------------------
class BaseNamedEntityRecognizer (object):
    """
    Is: an abstract base class for classes that implement or use a specific
    	tool to do NER.
    Does: doEntityRecognition for specific concept types on a list of documents
	  get counts/summaries of the entities mapped to concepts across docs. 

	  Documents are represented by an object that has .docId & .text
	    attributes (typically the docId would be a pubmed ID, but it could
	    be anything for our purposes here)
    """
    def __init__(self, concepts=allConcepts,	# {concept_name: T/F }
	):
			# list of concepts to map to
	self.concepts = [ c for (c,b) in concepts.items() if b == True ]

			# For each concept, keep
			#   count of individual entity names mapped &
			#   count of docs with at least one entity mapped
			# { concept_name: { 'numEntities' : n, 'numDocs': n} }
	self.conceptCounts = dict( [ [c, {'numEntities':0, 'numDocs': 0}]
						    for c in self.concepts] )

			# For each distinct entity name, keep count of
			#   num of times it was mapped to its concept
			#   & num docs with this entity mapped
			# { entity_name: { 'timesMapped': n, 'numDocs': n } }
	self.entityCounts =  {}

			# For each concept, keep track of the most recent doc
			#   that had an entity_name mapped to that concept.
			# Used to count docs that involve a given concept_name
			# { concept_name: most recent docId w/ this concept }
	self.mostRecentDocId = dict([ [c, None] for c in self.concepts ])
    # --------------------------

    def doEntityRecognition(self,
			    docs, # [ doc ], each doc obj has .docId and .text
	):
	""" Abstract method to do NER on the list of docs.
	    Returns parallel array to docs:
		[ { 'docId':    string,
		    'nerText' : text w/ NER concepts replacing entity_names,
		    'mappings': [{'entity_name': of the entity replaced,
				 'concept': name of concept
				 'start':  0 based idx of entity_name start
						 in doc text
				 } ]
		} ]
	"""
	return [ ]
    # --------------------------

    def getConceptCounts(self):
	return self.conceptCounts

    def getEntityCounts(self):
	return self.entityCounts
    # --------------------------

    def _countEntityRecognition(self,
		      concept,
		      entity,
		      docId,
	):
	""" Count the mapping of 'entity' as an instance of 'concept' in
		document 'docId'
	"""
	# is this a new doc for this concept?
	if docId == self.mostRecentDocId[concept]:
	    docIncrement = 0		# not new, don't increment doc count
	else:
	    docIncrement = 1		# new doc, count it
	    self.mostRecentDocId[concept] = docId

	# update concept Counts
	d = self.conceptCounts[concept]
	d['numEntities'] += 1
	d['numDocs']     += docIncrement

	# update entity Counts
	if not self.entityCounts.has_key(entity):
	    self.entityCounts[entity] = {'timesMapped' : 1, 'numDocs' : 1}
	else:
	    d = self.entityCounts[entity]
	    d['timesMapped'] += 1
	    d['numDocs']     += docIncrement
    # --------------------------
# end BaseNamedEntityRecognizer ------------

class TestNamedEntityRecognizer(BaseNamedEntityRecognizer):
    """
    Is: a simple test NER
    """
    entity_map = { 'Pax4' : geneProteinConcept,	# entities mapped to concepts
		 'Pax5' : geneProteinConcept,
		 'Pax6' : geneProteinConcept,
		 'brain': anatomyConcept,
		 'heart': anatomyConcept,
		}
    # --------------------------

    def doEntityRecognition(self,
			    docs, # [ doc ], each doc obj has .docId and .text
	):
	""" See abstract method in BasenamedEntityRecognizer
	"""
	results = []
	for doc in docs:

	    nerText = doc.text		# will be converted text
	    mappings = []		# list of instances of entity-concept
	    for ent, con in self.entity_map.items():
		l = len(ent)
		start = 0		# where to start search for entities
		idx = doc.text.find(ent, start)

		while idx != -1:
		    self._countEntityRecognition(con, ent, doc.docId)
		    nerText = nerText.replace(ent, con)
		    mappings.append({'entity_name':ent, 'concept':con,
				     'start':idx})
		    start = idx + l

		    idx = doc.text.find(ent, start)

	    results.append({'docId': doc.docId,
			    'nerText': nerText ,
			    'mappings': mappings } )
	return results

# end TestNamedEntityRecognizer ------------

class TestDoc (object):
    def __init__(self, id, text):
	self.docId = id
	self.text = text

# --------------------------
if __name__ == "__main__": 
    # some test code
    ner = TestNamedEntityRecognizer()
    doc1 = TestDoc('doc1', 'this is about Pax6 and Pax5. Pax6 is my favorite')
    doc2 = TestDoc('doc2', 'Pax5 is expressed in eye but not heart. ')

    rslts = ner.doEntityRecognition([doc1,doc2])
    print "doc1: '%s'" % doc1.text
    print "doc2: '%s'" % doc2.text
    print json.dumps(rslts, sort_keys=True, indent=4)
    print json.dumps(ner.getConceptCounts(), sort_keys=True, indent=4)
    print json.dumps(ner.getEntityCounts(), sort_keys=True, indent=4)
