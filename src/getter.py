import optparse
import sys
from typing import Iterator
import pybliometrics
import itertools

from pybliometrics.scopus import *
import pybliometrics.scopus

parser = optparse.OptionParser()

parser.set_usage("Usage: getter.py [doi 1] [doi 2] ...")
parser.add_option("-s", "--silent", action="store_true", help="silence print messages")

#map from readable key names to the names required to collect them from different indexes
REQUEST_FIELDS_TO_COLUMN_NAMES = {
  #ChatGPT's true purpose!
  "affiliation": ["affiliation"],  # Correct AbstractRetrieval field for affiliations
  "aggregation type": ["aggregationType"],  # Type of document (journal, book, etc.)
  "author keywords": ["authkeywords"],  # Author-specified keywords
  "authors": ["authors"],  # List of authors
  "publication date": ["coverDate"],  # Date of publication
  "citedby count": ["citedby_count"],  # Citation count
  "chemicals": ["chemicals"],  # Chemical data associated with the paper
  "conference": ["confname"],  # Conference name (if applicable)
  "copyright": ["copyright"],  # Copyright information
  "copyright owner": ["copyright_type"],  # Owner of the copyright
  "correspondence": ["correspondence"],  # Corresponding author's details
  "funding": ["funding"],  # Funding information
  "language": ["language"],  # Language of the document
  "open access": ["openaccess"],  # Open access status
  "publication name": ["publicationName"],  # Name of the journal or publication source
  "publisher": ["publisher"],  # Publisher of the document
  "reference count": ["refcount"],  # Reference count
  "references": ["references"], # References list
}

def scopus_abstract_to_top_columns(abstract:AbstractRetrieval):
  return {key: getattr(abstract, field[0], None) for key, field in REQUEST_FIELDS_TO_COLUMN_NAMES.items()}

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
COLUMNS_BLUEPRINT = {
  "affiliation" : (3, ["id", "name", "city", "country"]),
  "aggregation type": (None, [""]),
  "author keywords": (10, [""]),
  "authors": (6, ["auid", "indexed name", "surname", "given name", "affiliation"]),
  "publication date": (None, ["", "", ""]), #replace when you figure out the date format
  "citedby count": (None, [""]),
  "chemicals": (0, ["source", "chemical name"]),
  "conference": (None, [""]),
  "copyright": (None, [""]),
  "copyright owner": (None, [""]),
  "correspondence": (2, ["surname", "initials", "organization", "country", "city group"]),
  "funding": (3, ["agency", "agency id", "string", "funding id", "acronym", "country"]),
  "language": (None, [""]),
  "open access": (None, [""]),
  "publication name": (None, [""]),
  "publisher": (None, [""]),
}
def custom_formatter(option_group:optparse.OptionGroup, formatter):
  return f"{option_group.title}:\n\n{option_group.get_description()}"
ColumnsOptionsGroup = type("FunnyGroup", (optparse.OptionGroup, ), {"format_help": custom_formatter})
group = ColumnsOptionsGroup(parser, "Column Options",f""" -c COLUMN:COUNT
 -x EXCLUDE
                    
  For example:
    -c authors:10,chemicals:1 will result in 10 author columns and 1 checmical columns for each source
    -c collaborators:10 access will result in 10 collaborator columns
    -x "publisher,publication name" will result in no publisher or publication name columns
    -x "author keywords,publisher" -c "chemicals:1,author keywords:10" will result in no author keywords or publisher columns, and 1 chemicals column
  
  The available columns are {", ".join(map(lambda s: f'"{s}"', list(COLUMNS_BLUEPRINT.keys())))}
  By default, {", ".join(filter(lambda s: s != "", map(lambda pair: f'"{pair[0]}" has {pair[1][0]} columns' if pair[1][0] != None else "", COLUMNS_BLUEPRINT.items())))}, and no other columns can be counted
  No other columns can have counts supplied.
""")

def set_top_rows(counts_str:str, excludes_str:str) -> dict:
  columns = COLUMNS_BLUEPRINT.copy()

  counts = counts_str.split(",")

  for c in counts:
    pair = c.split(":")
    match len(pair):
      case 0: continue
      case 1:
        if pair[0] == "": continue
        sprint(f'"{pair[0]}" has too few identifiers! syntax: ["COLUMN:COUNT"], your syntax: "COLUMN" (run with -h or --help for more info)')
        exit() #no tolerance
      case 2:
        v = columns.get(pair[0])

        if v == None:
          sprint(f'Cannot number column "{pair[0]}" because that column does not exist! (run with -h or --help for more info)')
          exit()

        if v[0] == None:
          sprint(f'Column "{pair[0]}" is not countable! (run with -h or --help for more info)')
          exit()
        
        columns[pair[0]] = (pair[1], v[1])
      case _other:
        sprint(f'"{pair[0]}" has too few identifiers! syntax: ["COLUMN:COUNT"], your syntax: "COLUMN:COUNT:other stuff..." (run with -h or --help for more info)')
        exit()
  
  excludes = excludes_str.split(",")

  for e in excludes:
    if e == "": continue

    v = columns.get(e)

    if v == None:
      sprint(f'Cannot remove column "{pair[0]}" because that column does not exist! (run with -h or --help for more info)')
      exit()
    
    columns.pop(e)
  
  return columns

#pass 'META' as a temp hack, the view should be configurable by users using the scopus option
def construct_scopus_abstract(doi, refresh, view='META') -> Optional[AbstractRetrieval]:
  try:
    return AbstractRetrieval(doi, refresh, view)
  except:
    return None #pybibliometrics has a dogwater error system that makes it not possible to catch and recover from errors gracefully. Oh well!


def flatten_scopus_abstract(abstract:AbstractRetrieval, columns:dict) -> str:
  d = scopus_abstract_to_top_columns(abstract)

  for k in list(d.keys()): #safe iteration since d is going to be modified
    v = columns.get(k)
    if v == None: 
      d.pop(k)
      continue

    v_d = d[k]
    if v_d is Iterator[str]:
      d[k] = list(v_d)
    else:
      d[k] = [str(v_d)]

    if v[0] == None:
      continue
    
    d[k] = list(itertools.repeat(v_d, int(v[0])))

  return d

#lambdas to process a doi based on the citation index
CITATION_INDEX_CHOICES = {
  "scopus": lambda doi, refresh, columns:  
    flatten_scopus_abstract(construct_scopus_abstract(doi, refresh), columns) 
}
parser.add_option("-i", "--index",
  type="choice",
  choices=list(CITATION_INDEX_CHOICES.keys()),
  default=list(CITATION_INDEX_CHOICES.keys())[0],
  help="pick which citation index will be used for gathering full text and metadata"
)

group.add_option("-c", "--column-counts", 
  default="",
)
group.add_option("-x", "--column-exclude",
  default="",
)
parser.add_option_group(group)

parser.add_option("-r", "--refresh", type="int", default=-1,
  help="when dois are retrieved from cached files, specify the number of days after which the abstract will be re-requested, or -1 to never refresh"
)

(options, args) = parser.parse_args()

def sprint(s:str) -> None:
  if not options.silent: print(s)
def shelp() -> None:
  if not options.silent: parser.print_help()

refresh:int | bool = options.refresh if options.refresh >= 0 else False

index:str = options.index
if index == "scopus":
  pybliometrics.scopus.init()

#set columns for output
columns = set_top_rows(options.column_counts, options.column_exclude)

# reading from the standard input for extra doi links if no file is provided
# or appending to the provided file with extra arguments
# reading from stdin can be problematic. Condition from https://stackoverflow.com/questions/3762881/how-do-i-check-if-stdin-has-some-data
stdios = sys.stdin.read().splitlines() if (not sys.stdin.isatty()) else []
dois = itertools.chain(stdios, args)

i = 0
for d in dois:
  print(CITATION_INDEX_CHOICES[index](d, refresh, columns))
  i += 1
sprint(f"Finished with {i} records")
