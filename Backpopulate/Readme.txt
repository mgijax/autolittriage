This is for TR 12933.
Want to back populate PDFs for "mice" articles that curators did NOT select as 
relevant for MGI so we have more negative training samples to work with when
we get to implement automated tagging.

Per Jackie, we can query for the MGI journals for years 2010-2016 and assume
any articles with "mice" that were not selected for MGI are negative examples.

This is a one-off, one time thing once we get it right. Although it has taken
more time than I care to admit.

Most straight forward way to start this is to see what we can get from PMC
open access. Lets see how many PDFs we can actually get.
At some point we could consider crawling journal sites, but I don't want to 
do that.

Files:

backpopulate.py is the script for pulling PDFs from PMC OA

download_pdf.sh is adapted version of 
	https://github.com/mgijax/pdfdownload/blob/master/download_plos.py
	Actually hits the OA ftp site to get files
	(called from backpopulate.py)

find_pdf_in_tar.py has logic for finding the article PDF file from downloaded
	tar files. Many tar files have multiple PDFs :-(
	This is called from downlaod_pdf.sh.
	Can write to a log file so you can see the choices it makes,
	    setenv FIND_PDF_LOG filename

getTarFromPMID.sh is a quick script for pulling down a tar file from OA for 
	a given reference ID. I use this to inspect example tar files.

getMgiPubmedIDs.py is script to pull pubmed IDs for articles that are already
	in MGI. We only want to back populate articles that are not in MGI yet.
	So backpopulate.py skips downloading these articles.

mgiJournals*.txt are list of MGI journal (names) that curators monitor.
	These are the journals backpopulate.py should search for in OA.
	This list was pulled from:
	http://mgiprodwiki/mediawiki/index.php/cur:Primary_Triage_Assignments
	Might need to break these up into smaller subsets so backpopulate.py
	doesn't have too many to do at once.
	Plos 1 should be in a category by itself as it has lots of articles
	mgiJournals.clean.txt has the MGI journals that are not in PMC removed.

pmcJournals.csv is a list of journals that are in PMC (pulled from PMC website)
pmcJournalNames.csv is just the journal names pulled from that
	Use these to matchup MGI journal names with PMC. Sometimes they don't
	match, and I need to correct the journal name to query PMC.

oa_*.txt are files downloaded from the PMC ftp site that list the ftp site
	location of all OA files (PDFs) to download (the files are spread out
	over the ftp site). 
	I was trying to see if it was quicker to search these local .txt files
	to find where the PDFs are rather than using the OA API.
	But since the .txt files are so huge, they are slower to use.
	But maybe there is something more clever to do with them (load them
	into a python dictionary?). I haven't spent any time on that.

	This file is used by getTarFromPMID.sh to download tar files to inspect.

non-comm_use... is a directory of downloaded extracted text files from OA.
	Some articles have text extracted from PDFs by OA. I wanted to see
	what this looks like. It is odd, often the title and abstract are
	missing. So I think this is no help, and using it would give extracted
	text that is quite different from running our own text extractor on
	PDFs.

Running the backpopulate process.
    Run on bhmgiapp01.jax.org:
	/data/Jim_PDFs/PDFs is where where output goes
    Logging to /data/Jim_PDFs/download.log
    Logging find_pdf_in_tar.py decision so /data/Jim_Pdf/findpdf.log

	setenv FIND_PDF_LOG /data/Jim_PDFs/findpdf.log

    Invoking backPopulate.py from the directory where all the scripts live.
    Running small subsets of journals at a time.

    backPopulate.py -v -o /data/Jim_PDFs/PDFs journallistfile | tee -a /data/Jim_PDFs/download.log

    PLOS One will be handled separately due to its volumn of articles.
    Will need to break the PMC query in backPopulate.py into separate years.
    (for the other journals it does 2010-2016 in one query)


Lessons:
0) invoking download_pdf.sh caused me pain. From backpopulate.py, the quoting
    of "ftp://blah..." caused curl to treat 'ftp:// as the protocol. took
    me a long time to find (since it worked from the command line) that the
    "'" was being treated as part of the protocol name!
1) Jon's Dispatch.py to call multiple download_pdf.sh at once is good.
    maxProcesses=10 gives a little less than 1 second per pdf (=5 is close).
    Otherwise, 1 at a time ~ 4 seconds.
2) trying to find the correct PDF from the downloaded tar.gz files is tricky.
    PDF file naming varies by journal and article (various images/supp data
    files are PDFs too).
    find_pdf_in_tar.py is script for this logic, called from download_pdf.sh.
    Won't really be able to evaluate this perfectly until we start trying to 
    extract DOI IDs from the extracted text. The ones we cannot find IDs for
    will likely be the inaccurately selected supp data PDFs.
3) If a journal/search params match TOO many articles, backPopulate.py seems
    to die with the message "Killed". I have no idea what is happening, but
    breaking up the search into smaller date ranges seems to solve the problem.
    Two offenders:  "Science Reports" and "Plos One"
    Not sure what the max is, somewhere 2500-8000
