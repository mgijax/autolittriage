Using machine learning to automate literature triage tasks.

Backpopulate/  
    - code for getting old articles that curators have not selected in the past.
	These are negative, non-MGI-relevant articles.

Lessons Learned and Where We Are

Understanding Vectorizers
    vect = CountVectorizer( stop_words="english", ngram_range=(1,2))
    * tokenized 1st (e.g., break/remove punct), stopwords are removed,
	then ngrams built, then min_df/max_df applied

Dec 5 2018: vectorizer things:
    in extracted text:
	** *** and **** can appear as tokens aa aaa and aaaa
	+/- can appear as "ae"
	might want to remove doi:... in addition to URLs
	"knock in" and "knock down" are fairly common ("knock" in 5.3% docs)


Previous thinking for python scripts in MLtextTools:
    * getTrainingData.py would get a delimited file of samples
    * preprocessSamples.py would massage the data in the delimited file(s)
    * populateTrainigDirs.py would take a massaged delimited file and populate
	the dirs that sklearn's load_files() wants.
    Would it be better to have getTrainingData populate text files in the dirs
    and massage the data in place (or into additional cooked files)?

    BUT MLtextTools already has stuff in place, so lets keep with that 
    paradigm. Can always run populateTrainingDirs.py at any time to generate
    the text files to look at.
    	- should add parameter to specify file extension (done)
	- should make it not assume class names are 'yes' 'no' (done)

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
Dear Diary:

Dec 5, 2018
    Grabbed dataset to use going forward (for now)

    Idea: should write a script to calculate recall foreach curation group.
	Note, cannot really do precision since all the papers for each
	curation group are already "Keep" (so there are no false positives)

Dec 6, 2018
    Cannot do ngrams (1,3) - blows out the memory on my Mac

    Tried not removing stopwords and using feature counts instead of binary,
    these do not seem to be helpful at this point...

    Analyzed F-scores in https://docs.google.com/spreadsheets/d/1UpMNN4Qj1Ty9pYiQ4ZBspq2fef2qTeybHZMDc35Que8/edit#gid=1787124464

    Decided best for reporting "success" is F2 with values > 0.85.

    Still using F4 during gridsearch to weigh results toward recall, but
    this is questionable.

Dec 7, 2018
    using Dec5/Proc1
    Seemingly good, out of the box pipeline:  2018/12/07-09-21-48  SGDlog.py
    alpha = 1
    min_df = .02
    ngrams = (1,2)
    stopwords = english
    binary
    Gets (test) Precision: .61, Recall: .91, F2: .83

    Looking at false negative 28228254
	some Fig legends are split across page boundaries (so only get 1st part).
	Supplemental figures won't be found because they start with "Supplemental
	Figure" instead of just "Figure".
	"mice" only occurs in figure legend text skipped because of the above
	reasons & not in title/abstract

	Maybe we should omit "mice" as a feature since these are all supposed to
	be mice papers anyway ??

	Need to look at more FP FN examples examples examples examples
    false neg 27062441
	indexed by pm2gene, not selected for anything else. Monica says she
	would not select it a relevant since it is about human protein. 
	So this is really a true negative.
	Maybe we want to remove these from the whole raw set?

    Text transformations
	Looking at Jackie's 1-cell, one-cell, ... these seem relevant.
	should add these
    Changes
	* figureText.py - to include figure paragraphs that begin "supplemental
	    fig"
	* omit doi Ids along with URLs

Dec 8, 2018
    using Dec5/Proc2

    added more feature transformations
	1-cell ...
	knock in (in addition to knock-out)
	gene trap

    gets us to precision 60, recall 92

    Need to look at Debbie's "oma" transformations.
	In the current set of features, there is only one feature: carcinoma
	- but maybe if we collapse the other oma's, this feature would boosted.
	But have to factor out glaucoma. Are there others?
	Need to investigate.
Dec 10, 2018
    Added all the MTB "oma"s to feature transformation --> "tumor_type"

    On classifier prior to these additional feature transforms, investigating
    some FN
	27062441 - predicted discard, IS actually discard - discarded after I
			grabbed the data set
	26676765 - only pm2gene - probably not relevant - check
	26094765 - only pm2gene
	12115612 - text extracted ok. Need curator to review
    looking at some FP
	28538185 - Cell Reports - fig 3 legend text lost due to funky splitting
	    across pages, but other figures intact. Need curator to reviewj
	28052251 - Cell Reports - fig 2 partially lost due to split
	28614716 - Cell Reports - fig 1,3 partially lost due to split
	28575432 - Endocrinology - just a "news and reviews" very short
	28935574 - lots of fig text missing: 1,2,4,5,7,12,13 - seems trouble
	    finding beginning of fig text (only finding "Figure x"

    On classifier with new tumor_type transformation: no improvement of
	precision and recall: 61 and 92
	interestingly "tumor_typ" is a highly negative term (???)

Dec 11, 2018
    I want to see how well the relevance automation works for papers
    selected by the different groups.

    Wrote tdataDocStatus.py to pull article curation statuses out of the db.
    Wrote tdataGroupRecall.py to use those statuses + a prediction file compute
	the recall for papers selected for each curation group.

    based on current predictions for the current test set:
    Recall for papers selected by each curation group
    ap_status      selected papers:  1658 predicted keep:  1584 recall: 0.955
    gxd_status     selected papers:   167 predicted keep:   166 recall: 0.994
    go_status      selected papers:  1910 predicted keep:  1796 recall: 0.940
    tumor_status   selected papers:   178 predicted keep:   132 recall: 0.742
    qtl_status     selected papers:     7 predicted keep:     5 recall: 0.714
    Totals         selected papers:  2268 predicted keep:  2082 recall: 0.918

    The smaller number of papers for tumor and GXD match the smaller number
    of papers actually chosen/indexed/full-coded in the database since
    Oct 2017.  Roughly 10% of A&P and GO.

    Makes me think we need to look at the distributions in the test/validation
    sets from two axes (at least):
	by journal - and really should be by keep/discard by journal
	by curation group selection
    and make sure they match the distributions of all the data since Oct 2017.
    (it looks like they do for curation group selection)

Dec 12, 2018
    Looking at papers indexed for GO by pm2geneload that have not been deemed
    relevant by any curator...
	select distinct a.accid pubmed
	from bib_refs r join bib_workflow_status bs on
			    (r._refs_key = bs._refs_key and bs.iscurrent=1 )
	join bib_status_view bsv on (r._refs_key = bsv._refs_key)
	     join acc_accession a on
		 (a._object_key = r._refs_key and a._logicaldb_key=29 -- pubmed
		  and a._mgitype_key=1 )
	where 
	(bs._status_key = 31576673 and bs._group_key = 31576666 and 
	    bs._createdby_key = 1571) -- index for GO by pm2geneload
	and bsv.ap_status in ('Not Routed', 'Rejected')
	and bsv.gxd_status in ('Not Routed', 'Rejected')
	and bsv.tumor_status in ('Not Routed', 'Rejected')

    Finds 1758 papers. Seems like these should be removed from the sample set
    because we don't know for sure that these are really MGI relevant.
    (1758 is about 3.5% of our sample papers)

dec 19, 2018
    Changed tdataGetRaw.py to skip the pm2gene references as above.
    Used that to grab updated date in Data/dec19.

    Retraining/evaluating get tiny improvement:
    2018/12/19-12-46-56     PRF2,F1 0.62    0.92    0.84    0.74    SGDlog.py

    Recall for papers selected by each curation group (FOR TEST SET PREDS)
    ap_status      selected papers:  1664 predicted keep:  1592 recall: 0.957
    gxd_status     selected papers:   163 predicted keep:   160 recall: 0.982
    go_status      selected papers:  1789 predicted keep:  1696 recall: 0.948
    tumor_status   selected papers:   187 predicted keep:   142 recall: 0.759
    qtl_status     selected papers:     4 predicted keep:     4 recall: 1.000
    Totals         selected papers:  2153 predicted keep:  1989 recall: 0.924

    Added initial set of cell line transformations - those that are cell line
    prefixes. No improvement.

    Realized I'd like to see what these group recall numbers look like for
    the training and validation sets. To get these, need a longer time frame
    of paper statuss. Need to update tdataGetStatus.py for earlier date range

Dec 20, 2018
    changed tdataGetStatus.py as above. Interesting, a little worse:
    Recall for papers selected by each curation group (FOR TRAINING SET PREDS)
    ap_status      selected papers: 17877 predicted keep: 16976 recall: 0.950
    gxd_status     selected papers:  2019 predicted keep:  1993 recall: 0.987
    go_status      selected papers: 16491 predicted keep: 15365 recall: 0.932
    tumor_status   selected papers:  1735 predicted keep:  1286 recall: 0.741
    qtl_status     selected papers:   137 predicted keep:    74 recall: 0.540
    Totals         selected papers: 21544 predicted keep: 19602 recall: 0.910

    No idea what that means!

    wrote wrapper scripts for extracting fig text and preprocessing the train,
    test, & val data files

    added cell line names (not prefixes) to transformations. No change really.

    Looking at tumor papers/stats. Why is tumor recall so low? The counts of
    papers and papers by status are very close to gxd papers.
    So it doesn't seem that the training/test sets would somehow be skewed to
    not include enough tumor papers (???). 
    However it does seem that tumor papers are harder to recognize (hence more
    false negatives).

Dec 21, 2018
    Updated tdataGroupRecall.py to optionally output rows that combine a
    paper's prediction with it curation statuses.
    So you can look at tumor FN or AP FN, etc.
    Not sure how much it helps.
    BUT the vast majority of tumor FN  (41 of 45) are not selected for any
    other group and the vast majority of TP are selected by other group.
    I guess this just clarifies, tumor papers are harder to
    detect. If they are relevant to any other group, they are easier to detect.
    This seems less true for GXD AP FN (just by eyeball).:w
    
    

