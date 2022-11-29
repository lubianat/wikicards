import json
from pathlib import Path

from wikidata2df import wikidata2df

HERE = Path(__file__).parent.resolve()

query = """
SELECT DISTINCT
?p ?idLabel ?formatter_url  
WHERE {
  ?p wdt:P31/wdt:P279* wd:Q22988603 . 
  ?p wdt:P1630 ?formatter_url . 
  ?p rdfs:label ?idLabel .
  FILTER (Lang(?idLabel) = "en")
}
"""

df = wikidata2df(query)

formatter_dict = {}
for i, row in df.iterrows():
    formatter_dict[row.idLabel.replace(" ", "_")] = row.formatter_url

HERE.joinpath("formatter_dict.json").write_text(
    json.dumps(formatter_dict, indent=4, sort_keys=True), encoding="UTF-8"
)
