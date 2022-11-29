import requests

item_json = requests.get(
    f"https://www.wikidata.org/wiki/Special:EntityData/Q283350.json"
).json()

values = extract_value_from_wikidata_json(item_json, "P638")


print(values)
