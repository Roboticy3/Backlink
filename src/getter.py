import optparse
import sys
import pybliometrics
import itertools

from pybliometrics.scopus import *

parser = optparse.OptionParser()

parser.set_usage("Usage: getter.py [doi 1] [doi 2] ...")
parser.add_option("-s", "--silent", action="store_true", help="silence print messages")

CITATION_INDEX_CHOICES = {
  "scopus": lambda: pybliometrics.scopus.init()
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

stdios = sys.stdin.read().splitlines()
dois = itertools.chain(stdios, args)

for d in dois:
  ab = AbstractRetrieval(d)
  print(ab)

