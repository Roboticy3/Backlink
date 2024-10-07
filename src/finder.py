import optparse
import requests
import re

OCR_CITING_DOI = re.compile("'citing': '([^']*)'")
def opencitations_request_to_citing_dois(request_json:str):
  return map(
    lambda match : match.group(1), 
    OCR_CITING_DOI.finditer(request_json)
  )

parser = optparse.OptionParser()
parser.set_usage("Usage: finder.py [doi] [options]")
parser.add_option("-s", "--silent", action="store_true", help="silence print messages")

(options, args) = parser.parse_args()
def sprint(s:str) -> None:
  if not options.silent: print(s)
def shelp() -> None:
  if not options.silent: parser.print_help()

if (len(args) < 1) : 
  sprint("Not enough arguments!")
  shelp()
  exit()

doi = args[0]

citations_uri = f"https://opencitations.net/index/coci/api/v1/citations/{doi}"

request = requests.get(citations_uri)
citing_dois = opencitations_request_to_citing_dois(str(request.json()))
for d in citing_dois:
  d_req = requests.get(f'https://dx.doi.org/{d}', headers={'Accept':'text/bibliography'}, params={'style':'bibtex'})
  print(d_req.text)