from Bio import Entrez
import urllib
import requests
import wikipedia
import json
import xmltodict


def get_entrez_summary(entrez_id, email="tiago.lubiana.alves@usp.br"):
    Entrez.email = email
    handle = Entrez.esummary(db="gene", id=entrez_id)

    record = Entrez.read(handle)
    return record["DocumentSummarySet"]["DocumentSummary"][0]["Summary"]


def get_wikipedia_summary(page_name):
    print(page_name)
    r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_name}")
    print(r.text)
    return json.loads(r.text)


def get_uniprot_info(uniprot_id):

    r = requests.get(f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.xml")
    uniprot_dict = xmltodict.parse(r.text)
    uniprot_info = {}
    for i in uniprot_dict["uniprot"]["entry"]["comment"]:
        if i["@type"] == "alternative products":
            uniprot_info["isoforms"] = i["isoform"]
        if i["@type"] == "domain":
            uniprot_info["domain_info"] = i["text"]["#text"]
    return uniprot_info
