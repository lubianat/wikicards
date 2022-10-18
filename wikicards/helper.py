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
    uniprot_info["ptm_info"] = []
    uniprot_info["function_info"] = []

    for i in uniprot_dict["uniprot"]["entry"]["comment"]:
        if i["@type"] == "alternative products":
            uniprot_info["isoforms"] = i["isoform"]
        if i["@type"] == "domain":
            uniprot_info["domain_info"] = i["text"]["#text"]
        if i["@type"] == "PTM":
            if "#text" in i["text"]:
                uniprot_info["ptm_info"].extend(i["text"]["#text"].split("."))
            else:
                uniprot_info["ptm_info"].extend(i["text"].split("."))
        if i["@type"] == "function":
            if "#text" in i["text"]:
                uniprot_info["function_info"].extend(i["text"]["#text"].split("."))
            else:
                uniprot_info["function_info"].extend(i["text"].split("."))
    uniprot_info["function_info"] = list(filter(None, uniprot_info["function_info"]))
    print(uniprot_info["function_info"])
    uniprot_info["ptm_info"] = list(filter(None, uniprot_info["ptm_info"]))
    return uniprot_info
