import optparse
import sys
import pybliometrics
import itertools

from pybliometrics.scopus import *

parser = optparse.OptionParser()

parser.set_usage("Usage: getter.py [doi 1] [doi 2] ...")
parser.add_option("-s", "--silent", action="store_true", help="silence print messages")

# The top 2 rows of the output csv with all the metadata of each article,
# designed for scopus AbstractRetrieval, may have to modify later to accept different citation indices
# The top row represents general categories of data as listed by https://pybliometrics.readthedocs.io/en/stable/classes/AbstractRetrieval.html#documentation, and https://dev.elsevier.com/sc_abstract_retrieval_views.html
# some views are removed for the sake of redundance
# FORMAT:
# "data category" : (columnns, subcolumn names). 
# If "columns" is None, then the subcolumn names are laid out once
# If "columns" is a number, then this is the default number of times the subcolumns are laid out in a row
# The user can specify, for data categories with column numbers, a different number of columns to their liking
# After this, the total number of columns, and what data to put in which column for each row, can be computed
top_rows = OrderedDict({
  "affiliation" : (3, set(["id", "name", "city", "country"])),
  "aggregation type": (None, set([""])),
  "author keywords": (10, set([""])),
  "authors": (6, set(["auid", "indexed name", "surname", "given name", "affiliation"])),
  "publication date": (None, set(["", "", ""])), #replace when you figure out the date format
  "citedby count": (None, set([""])),
  "chemicals": (0, set(["source", "chemical name"])),
  "conference": (None, set([""])),
  "copyright": (None, set([""])),
  "copyright owner": (None, set([""])),
  "correspondence": (2, set(["surname", "initials", "organization", "country", "city group"])),
  "funding": (3, set(["agency", "agency id", "string", "funding id", "acronym", "country"])),
  "language": (None, set([""])),
  "open access": (None, set([""])),
  "publication name": (None, set([""])),
  "publisher": (None, set([""]))
})
def custom_formatter(option_group:optparse.OptionGroup, formatter):
  return f"{option_group.title}:\n\n{option_group.get_description()}"
Group = type("Group", (optparse.OptionGroup, ), {"format_help": custom_formatter})
column_group = Group(parser, "Column Options",f""" -c set counts for columns
 -x exclude columns
                    
  For example:
    -c authors:10,chemicals:1 will result in 10 author columns and 1 checmical columns for each source
    -c collaborators:10 access will result in 10 collaborator columns
    -x "publisher,publication name" will result in no publisher or publication name columns
    -x "author keywords,publisher" -c "chemicals:1,author keywords:10" will result in no author keywords or publisher columns, and 1 chemicals column
  
  The available columns are {", ".join(map(lambda s: f'"{s}"', list(top_rows.keys())))}
  By default, {", ".join(filter(lambda s: s != "", map(lambda pair: f'"{pair[0]}" has {pair[1][0]} columns' if pair[1][0] != None else "", top_rows.items())))}, and no other columns can be counted
  No other columns can have counts supplied.
""")

column_group.add_option("-c", "--column-counts", 
  default="",
)
column_group.add_option("-x", "--column-exclude",
  default="",
)
parser.add_option_group(column_group)

parser.add_option("-r", "--refresh", type="int", default=-1,
  help="when dois are retrieved from cached files, specify the number of days after which the abstract will be re-requested, or -1 to never refresh"
)

def flatten_scopus_abstract(abstract:AbstractRetrieval, columns:set[str]) -> str:
  return ""

CITATION_INDEX_CHOICES = {
  "scopus": lambda doi, refresh, columns:  
    flatten_scopus_abstract(AbstractRetrieval(doi, refresh), columns)
}
parser.add_option("-i", "--index",
  type="choice",
  choices=list(CITATION_INDEX_CHOICES.keys()),
  default=list(CITATION_INDEX_CHOICES.keys())[0],
  help="pick which citation index will be used for gathering full text and metadata"
)

(options, args) = parser.parse_args()

def sprint(s:str) -> None:
  if not options.silent: print(s)
def shelp() -> None:
  if not options.silent: parser.print_help()

refresh:int | bool = options.refresh if options.refresh >= 0 else False

def set_top_rows(columns_option:str):
  columns = columns_option.split(",")
  for c in columns:
    pair = c.split(":")
    if (len(pair) == 1):
      sprint(f"Column {c} has too few identifiers!")

# reading from the standard input for extra doi links if no file is provided
# or appending to the provided file with extra arguments
# reading from stdin can be problematic. Condition from https://stackoverflow.com/questions/3762881/how-do-i-check-if-stdin-has-some-data
stdios = sys.stdin.read().splitlines() if (not sys.stdin.isatty()) else []
dois = itertools.chain(stdios, args)

for d in dois:
  pass
