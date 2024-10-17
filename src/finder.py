import optparse
import os, sys, itertools, io
import typing
import requests
import re

#let the program be silenced for cleaner chaining with other programs
parser = optparse.OptionParser()
parser.set_usage("Usage: finder.py [doi] [options] [extra doi 1] [extra doi 2] ...\n\n"
"Extra dois will have their data found, even if they don't cite the first doi")
parser.add_option("-s", "--silent", action="store_true", help="silence print messages")

#function to 
OC_REQUEST_CITING_DOI_REGEX = re.compile("'citing': '([^']*)'")
def opencitations_request_to_citing_dois(request:requests.Response, catch:typing.Callable[[int], typing.Any], log:io.TextIOWrapper | None = None):

  #TODO! read log if it already has contents instead of requesting the internet

  #catch a bad error code
  if catch(request.status_code): return map()

  #find all the dois in the request
  try:
    request_string = str(request.json())
    if log: 
      print("Writing to citing log...")
      log.write(f'{request_string}')
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
    lambda doi, catch, log = None: 
      opencitations_request_to_citing_dois(
        requests.get(
          f"https://opencitations.net/index/coci/api/v1/citations/{doi}"
        ), catch, log
      )
  ),
}
parser.add_option("-i", "--citing-index", type="choice", 
  choices=list(CITATION_INDEX_CHOICES.keys()),  
  default=list(CITATION_INDEX_CHOICES)[0],
  help=f"pick the database I will use for finding all the citing publications ({"|".join(CITATION_INDEX_CHOICES)})"
)
parser.add_option("-l", "--citing-log", default="logs/citing_log.txt",
  help="the output of the request log for citing dois"
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
parser.add_option("-L", "--meta-log", default="logs/meta_log.txt",
help="the output of the request logs for citing dois"
)

#TODO! Column schemas:
### Given a json string, return either column headers or a single row in csv format:
### Headers will be at "depths" specified by -q. If q is 0-5, the output headers will have 5 rows.
### The first row will have the properties of the json object, the second the properties of those objects, etc.
### If some object contains an array, unspool the array into columns, with 5 elements by default
### If some object contains multiple objects and is on the last row, keep 5 elements by default
### If these objects have fewer than 5 elements, the columns are added in, and they are truncated if they are over.
DEFAULT_COLUMN_COUNT = 5
### The goal is to output csv headers and rows with a predictable number of columns for some arbitrary json.
### -c will specify counts for certain fields in the form [REGEX:COUNT]. These specifications should be adhered to on the fly, 
###   truncating or extending the output string based on how the counts regexes treat the current field being looked at.
### -x will exclude columns, override any behavior specified by -c, and be equivalent to specifying a count of "0" for the same columns.
### It would probably best to make a supporting program called jsontocsv.py or something similar.

#not sure how to write the help session for this
parser.add_option("-q", "--query-rows", type="string", default="1-3")

parser.add_option("-x", "--exclude", default="coredata", help="querying each doi returns a list of 'fields', named data, '-x coredata|link' will exclude any fields with names containing 'coredata' or 'link' from the output")
parser.add_option("-c", "--counts", default="", help="querying each doi returns a list of 'fields', named data. "
"Some fields contain lists. For spreadsheets to contain these lists, they have to have a predictable length. "
"'-c chemicals:3,author-keyword:2' will set the number of columns under fields containing 'chemicals' to 3, and the number of columns under fields containing 'author-keywords' to 2. "
"With no -c argument, the number of columns for each field will be the maximum entries found under that field over the dois")

(options, args) = parser.parse_args()

if options.silent: sys.stdout = open(os.devnull, 'w')

def catch_bad_status(status_code:int):
  if status_code != 200 and options.response_error_handling == "show-content": 
    print("response failed with code", status_code)
    return True
  return False

if (len(args) < 1) : 
  print("Not enough arguments!")
  parser.print_help()
  exit()

doi = args[0]

citing_dois = []
try:
  #if the request for citing dois is being logged, pass a log file to the request handler 
  with open(options.citing_log, 'w', encoding="utf-16") as f:
    citing_dois = CITATION_INDEX_CHOICES[options.citing_index](doi, catch_bad_status, f)
except Exception:
  print("Citing log", options.citing_log, "failed to open! Continuing with no meta log...")
  citing_dois = CITATION_INDEX_CHOICES[options.citing_index](doi, catch_bad_status)

def dois_to_responses(dois, index:str, key:str):
  params = {}
  match index:
    case "scopus": params = {"apiKey":key, "httpAccept":"application/json", "view":"META"}
  return map(lambda doi: CITATION_META_INDEX_CHOICES[index](doi, params), dois)

# reading from the standard input for extra doi links if no file is provided
# or appending to the provided file with extra arguments
# reading from stdin can be problematic. Condition from https://stackoverflow.com/questions/3762881/how-do-i-check-if-stdin-has-some-data
stdios = sys.stdin.read().splitlines() if (not sys.stdin.isatty()) else []
citing_dois = itertools.chain(stdios, citing_dois)

#TODO! convert a json string to comma seperated values based on a column schema.
def single_json_to_meta(response:requests.Response):  
  if catch_bad_status(response.status_code) and options.response_error_handling != "output-anyways":
    return None
  return str(response.json())

def dois_to_meta(citing_dois, log):
  print("Scanning citing publications found on",options.citing_index,"and publication data found on",options.meta_index,"...")
  responses = dois_to_responses(citing_dois, options.meta_index, options.key)
  meta:typing.Iterator[str] = []
  try:
    with open(log, "w", encoding="utf-16") as f:
      lmeta = list(filter(lambda json: json != None, map(single_json_to_meta, responses)))
      print("Writing",len(lmeta),"entries to meta log...")
      meta = lmeta
      for m in meta:
        f.write(f"{m}\n")    
  except:
    print("Meta log", log, "failed to open! Continuing with no meta log...")
    meta = filter(lambda json: json, map(single_json_to_meta, responses))
  
  return meta

meta = dois_to_meta(citing_dois, options.meta_log)