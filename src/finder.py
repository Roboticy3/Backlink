import itertools
import optparse
import os
import sys
from typing import Any, Callable
import requests
import re

#let the program be silenced for cleaner chaining with other programs
parser = optparse.OptionParser()
parser.set_usage("Usage: finder.py [doi] [options] [extra doi 1] [extra doi 2] ...\n\n"
"Extra dois will have their data found, even if they don't cite the first doi")
parser.add_option("-s", "--silent", action="store_true", help="silence print messages")

#function to 
OC_REQUEST_CITING_DOI_REGEX = re.compile("'citing': '([^']*)'")
def opencitations_request_to_citing_dois(request:requests.Response, catch:Callable[[int], Any]):
  
  if catch(request.status_code): return map()

  try:
    request_string = str(request.json())
  except:
    request_string = ""
  return map(
    lambda match : str(match.group(1)) , 
    OC_REQUEST_CITING_DOI_REGEX.finditer(request_string)
  )

#citation indices can be easily added here, 
#new names will automatically become choices for the -i argument, 
#maps to the function that will run when requesting a doi through that index
CITATION_INDEX_CHOICES = {
  "opencitations":(
    lambda doi, catch: 
      opencitations_request_to_citing_dois(
        requests.get(
          f"https://opencitations.net/index/coci/api/v1/citations/{doi}"
        ), catch
      )
  )
}
parser.add_option("-i", "--citing-index", type="choice", 
  choices=list(CITATION_INDEX_CHOICES.keys()),  
  default=list(CITATION_INDEX_CHOICES)[0],
  help=f"pick the database I will use for finding all the citing publications ({"|".join(CITATION_INDEX_CHOICES)})"
)

#output file can be specified
parser.add_option("-o", "--output", 
  default="data/finder.txt",
  help=f"pick the output file for the program"
)

parser.add_option("-k", "--key", default="",
  help="When accessing a private or credentialed API, this is argument should be supplied with the key that will allow remote access"
)

parser.add_option("-e", "--response-error-handling", type="choice", choices=["output-anyways","show-content","discard"],
  help="How Finder will respond to requests with bad status codes",
  default="show-content"
)

CITATION_META_INDEX_CHOICES = {
  "scopus":lambda doi, params: requests.get(f"https://api.elsevier.com/content/abstract/doi/{doi}", params=params)
}
parser.add_option("-I", "--meta-index", type="choice", choices=list(CITATION_META_INDEX_CHOICES.keys()), default=list(CITATION_META_INDEX_CHOICES)[0], help="select the source that data will be gathered from. "
"This only changes the url or the api query, the rest of the functionality of the program is based purely of the fields the query returns. See help on -x and -c.")

parser.add_option("-q", "--query-rows", type="int", default=3, help="")
parser.add_option("-x", "--exclude", default="coredata", help="querying each doi returns a list of 'fields', named data, '-x coredata|link' will exclude any fields with names containing 'coredata' or 'link' from the output")
parser.add_option("-c", "--counts", default="", help="querying each doi returns a list of 'fields', named data. "
"Some fields contain lists. For spreadsheets to contain these lists, they have to have a predictable length. "
"'-c chemicals:3,author-keyword:2' will set the number of columns under fields containing 'chemicals' to 3, and the number of columns under fields containing 'author-keywords' to 2. "
"With no -c argument, the number of columns for each field will be the maximum entries found under that field over the dois")

(options, args) = parser.parse_args()

if options.silent: sys.stdout = open(os.devnull, 'w')

def catch_bad_status(status_code:int):
  if status_code != 200 and options.response_error_handling == "show-content": print("response failed with code", status_code)

if (len(args) < 1) : 
  print("Not enough arguments!")
  parser.print_help()
  exit()

doi = args[0]

citing_dois = CITATION_INDEX_CHOICES[options.citing_index](doi, catch_bad_status)

def dois_to_jsons(dois, index:str, key:str):
  params = {}
  match index:
    case "scopus": params = {"apiKey":key, "httpAccept":"application/json", "view":"META"}
  return map(lambda doi: CITATION_META_INDEX_CHOICES[index](doi, params), dois)

# reading from the standard input for extra doi links if no file is provided
# or appending to the provided file with extra arguments
# reading from stdin can be problematic. Condition from https://stackoverflow.com/questions/3762881/how-do-i-check-if-stdin-has-some-data
stdios = sys.stdin.read().splitlines() if (not sys.stdin.isatty()) else []
citing_dois = itertools.chain(stdios, citing_dois)

i = 0
print("Scanning citing publications found on",options.citing_index,"and publication data found on",options.meta_index,"...")
with open("data/finder.txt", "w", encoding="utf-16") as f:
  for response in dois_to_jsons(citing_dois, options.meta_index, options.key):
    catch_bad_status(response.status_code)
    if response.status_code != 200 and options.response_error_handling != "output-anyways":
      continue
    f.write(str(response.json()))
    f.write("\n")
    i += 1
print("Finished scanning ", i, " entries")