-- SQL to get list of actual journal names out of db along with
-- counts of articles 
--   since jan 2010 (where we started back populated articles from)
--   since oct 2016 (where we started recent training set)

create temporary table tmp_journals_since
as
select  b.journal, count(*) as num_since_oct2016
from bib_refs b
where b.creation_date >= '10/01/2016'
group by b.journal
order by b.journal;

select  b.journal, count(*) as num_since_jan2010, b2.num_since_oct2016
from bib_refs b left outer join tmp_journals_since b2 on (b.journal = b2.journal)
where b.creation_date >= '01/01/2010'
group by b.journal, b2.num_since_oct2016
order by b.journal;

