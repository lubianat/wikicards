from Bio import Entrez
import requests
import json
import xmltodict

import base64
import io


def get_ontological_definition(curie):
    curie = curie.replace("_", ":")
    url = f"http://biolookup.io/api/lookup/{curie}"
    print(url)
    r = requests.get(url)
    data = r.json()
    print(data)
    return data["definition"]


def serve_pil_image(pil_img):

    img_io = io.BytesIO()
    pil_img.save(img_io, "jpeg", quality=100)
    img_io.seek(0)
    img = base64.b64encode(img_io.getvalue()).decode("ascii")
    img_tag = f'<img src="data:image/jpg;base64,{img}" class="img-fluid"/>'
    return img_tag


def get_entrez_summary(entrez_id, email="tiago.lubiana.alves@usp.br"):
    Entrez.email = email
    handle = Entrez.esummary(db="gene", id=entrez_id)

    record = Entrez.read(handle)
    return record["DocumentSummarySet"]["DocumentSummary"][0]["Summary"]


def get_wikipedia_summary(page_name):
    print(page_name)
    r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_name}")
    print(r.text)
    data = json.loads(r.text)
    return data


def get_uniprot_info(uniprot_id):

    r = requests.get(f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.xml")
    uniprot_dict = xmltodict.parse(r.text)
    uniprot_info = {}
    uniprot_info["ptm_info"] = []
    uniprot_info["domain_info"] = []

    uniprot_info["function_info"] = []

    for i in uniprot_dict["uniprot"]["entry"]["comment"]:
        if i["@type"] == "alternative products":
            uniprot_info["isoforms"] = i["isoform"]
        if i["@type"] == "tissue specificity":
            uniprot_info["expression"] = i["text"]["#text"]
        if i["@type"] == "domain":
            if "#text" in i["text"]:
                uniprot_info["domain_info"].extend(i["text"]["#text"].split("."))
            else:
                uniprot_info["domain_info"].extend(i["text"].split("."))
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
    uniprot_info["ptm_info"] = list(filter(None, uniprot_info["ptm_info"]))
    print(uniprot_dict["uniprot"]["entry"]["comment"])
    return uniprot_info
