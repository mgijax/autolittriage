#!/bin/sh
# quick script to:
#  given a pubmed ID
#  find its PMC Id and its location on the PMC OA ftp site
#  Download its tar file, unpack the file so we can look at its contents
#
# Actually this should work for PMC IDs too. It is just grepping the OA file.
#
# I'm using this to look into problems with choosing the correct PDF file from
#    the tar file.

#  $1 = pubmed ID to look up in OA (PMID:nnnnn)
pmid=$1
line=`grep $pmid /home/jak/work/Backpopulate/oa_file_list.txt`
fileloc=`echo "$line" | cut -f 1`
pmcid=`echo "$line" | cut -f 3`
#echo $line
#echo $fileloc
#echo $pmcid

curl ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/$fileloc  >${pmcid}.tar.gz
gunzip ${pmcid}.tar.gz
tar xvf ${pmcid}.tar
echo $pmcid
