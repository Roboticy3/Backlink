import optparse
import requests
import re

#let the program be silenced for cleaner chaining with other programs
parser = optparse.OptionParser()
parser.set_usage("Usage: finder.py [doi] [options]")
parser.add_option("-s", "--silent", action="store_true", help="silence print messages")

#function to 
OCR_CITING_DOI = re.compile("'citing': '([^']*)'")
def opencitations_request_to_citing_dois(request:requests.Response):
  try:
    request_string = str(request.json())
  except:
    request_string = ""
  return map(
    lambda match : str(match.group(1)) , 
    OCR_CITING_DOI.finditer(request_string)
  )

#citation indices can be easily added here, 
#new names will automatically become choices for the -i argument, 
#maps to the function that will run when requesting a doi through that index
CITATION_INDEX_CHOICES = {
  "opencitations":(
    lambda doi: 
      opencitations_request_to_citing_dois(
        requests.get(
          f"https://opencitations.net/index/coci/api/v1/citations/{doi}"
        )
      )
  )
}
parser.add_option("-i", "--citation-index", type="choice", 
  choices=list(CITATION_INDEX_CHOICES.keys()),  
  default=list(CITATION_INDEX_CHOICES.keys())[0],
  help=f"pick the database I will use for finding all the citing publications ({"|".join(CITATION_INDEX_CHOICES)})"
)

#output file can be specified
parser.add_option("-o", "--output", 
  default="data/finder.txt",
  help=f"pick the output file for the program"
)

(options, args) = parser.parse_args()

#define output functions based on the silent argument
def sprint(s:str) -> None:
  if not options.silent: print(s)
def shelp() -> None:
  if not options.silent: parser.print_help()

if (len(args) < 1) : 
  sprint("Not enough arguments!")
  shelp()
  exit()

doi = args[0]

citing_dois = CITATION_INDEX_CHOICES[options.citation_index](doi)

with open(options.output, "w", encoding="utf-16") as out:
  for d in citing_dois:
    out.write(f"{d}\n")