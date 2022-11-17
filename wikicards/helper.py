"""
Helper functions for the WikiCards Flask app.
"""
from Bio import Entrez
import requests
import json
import xmltodict

import base64
import io


def get_ontological_definition(curie: str) -> str:
    """
    Given a CURIE (Compact URI) for an OBO foundry concept, returns the description of it.
    Args:
      curie (str):  A compact URI for a biological concept.
    """
    curie = curie.replace("_", ":")
    url = f"http://biolookup.io/api/lookup/{curie}"
    result = requests.get(url)
    data = result.json()
    return data["definition"]


def serve_pil_image(python_image):
    """
    Saves a Python Image Library (PIL) image and outputs an html tag pointing to such image.

    """
    img_io = io.BytesIO()
    python_image.save(img_io, "jpeg", quality=100)
    img_io.seek(0)
    img = base64.b64encode(img_io.getvalue()).decode("ascii")
    img_tag = f'<img src="data:image/jpg;base64,{img}" class="img-fluid"/>'
    return img_tag


def get_entrez_summary(entrez_id: str, email="tiago.lubiana.alves@usp.br") -> str:
    """
    Retrieves the NCBI Entrez summary for a gene given its Entrez ID.
    Args:
      entrez_id (str): The NCBI Entrez ID of the target gene.
    """
    Entrez.email = email
    handle = Entrez.esummary(db="gene", id=entrez_id)

    record = Entrez.read(handle)
    return record["DocumentSummarySet"]["DocumentSummary"][0]["Summary"]


def get_wikipedia_summary(page_name: str) -> dict:
    """
    Retrieves a dict with core information for an Wikipedia page.
    Args:
      page_name: The title of the Wikipedia page of interest.
    """
    result = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_name}"
    )
    data = json.loads(result.text)
    return data


def get_uniprot_info(uniprot_id):
    """
    Parse and retrieve a subset of the information available on UniProt\
    for a target protein. 
    Args:
      uniprot_id (str): The UniProt ID of the target protein.
    """
    result = requests.get(f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.xml")
    uniprot_dict = xmltodict.parse(result.text)
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
    return uniprot_info
