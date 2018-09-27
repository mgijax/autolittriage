Using machine learning to automate literature triage tasks.

Backpopulate/  
    - code for getting old articles that curators have not selected in the past.
	These are negative, non-MGI-relevant articles.

Lessons Learned and Where We Are

NER thoughts
    Becas is very unreliable, down much of the time.
    Haven't found any other online tool (need to look some more).
    Pubtator does NER on pubmed abstracts and titles, but it won't do anything
	with figure text.
    I'm pondering doing some simple, easy to code, dictionary lookup approach
    myself.
	It doesn't have to be perfect, or even very good maybe.
	But where to get the dictionary? Some thoughts:
	    Build by hand from MGI gene symbols and ontology terms?
	    Pull mapping files for all of pubmed from Pubtator and distill
		out the entity mappings - easy to program, but a honking pile
		of data.
	    For our particular set of pubmed IDs, pull the mappings out of 
		Pubtator and apply those mappings to the figure text?
		(would be a much smaller set of mappings and likely more
		relevant/specific to our references??)

		I'm kind of liking this idea.
		(unfortunately, Pubtator doesn't do anatomy)

    I guess the first thing is to get an initial training pipeline built
	without NER.
...
