"""
Helper functions for the WikiCards Flask app.
"""
import base64
import io
import json
import re
import urllib
from io import BytesIO
from logging.config import dictConfig
from pathlib import Path
from typing import OrderedDict

import requests
import xmltodict
from Bio import Entrez
from flask.logging import default_handler
from helper import *
from jinja2 import Template
from PIL import Image
from wdcuration import get_statement_values, query_wikidata
from wikidata2df import wikidata2df

HERE = Path(__file__).parent.resolve()
QUERIES = HERE.joinpath("queries").resolve()
DICTS = HERE.joinpath("dicts").resolve()
FORMATTER_DICT = json.loads(DICTS.joinpath("formatter_dict.json").resolve().read_text())


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


def extract_value_from_wikidata_json(item_json, PID):
    """
    Extract values for a property from the full JSON for an item on Wikidata.
    Args:
      item_json: The full JSON for the item loaded as a Python dict.
      PID: The Wikidata PID for the property to be retrieved.

    """
    qid = list(item_json["entities"].keys())[0]
    claims = item_json["entities"][qid]["claims"]

    values_full = claims[PID]

    values_to_return = []
    for value in values_full:
        value_to_return = value["mainsnak"]["datavalue"]["value"]
        values_to_return.append(value_to_return)
    return values_to_return


def get_all_genes():
    all_genes_df = wikidata2df(
        "SELECT DISTINCT ?HGNC_gene_symbol WHERE {?item wdt:P353 ?HGNC_gene_symbol}"
    )
    all_genes = []
    for gene in all_genes_df["HGNC_gene_symbol"]:
        all_genes.append({"name": gene})
    all_genes = json.dumps(all_genes).replace('"name"', "name")
    all_genes = all_genes.replace('"', "'")
    return all_genes


def get_all_cells():
    query = (
        "SELECT DISTINCT ?itemLabel"
        '  (REPLACE(STR(?item), ".*Q", "Q") AS ?qid) '
        " WHERE {?item wdt:P7963 [] . "  # Cell Ontology ID
        "?item rdfs:label ?itemLabel . "
        "FILTER (LANG (?itemLabel) = 'en') }"
    )
    all_cells_df = wikidata2df(query)
    all_cells = []
    for _, row in all_cells_df.iterrows():
        all_cells.append({"name": row["itemLabel"], "id": row["qid"]})
    all_cells = json.dumps(all_cells).replace('"name"', "name")
    return all_cells


def get_all_diseases():
    query = (
        "SELECT DISTINCT ?itemLabel"
        '  (REPLACE(STR(?item), ".*Q", "Q") AS ?qid) '
        " WHERE {?item wdt:P31 wd:Q112193867 . "
        "?item rdfs:label ?itemLabel . "
        "FILTER (LANG (?itemLabel) = 'en') }"
    )
    all_diseases = get_all_of_a_kind_for_jinja(query)
    return all_diseases


def get_all_compounds():
    """
    Retrieves all chemical compounds of interest from Wikidata for the Flask dropdown menu.
    """
    query = (
        "SELECT DISTINCT ?itemLabel"
        '  (REPLACE(STR(?item), ".*Q", "Q") AS ?qid) '
        " WHERE {?item wdt:P31 wd:Q113681859 .  "
        "?item rdfs:label ?itemLabel . "
        "FILTER (LANG (?itemLabel) = 'en') }"
    )
    all_compounds = get_all_of_a_kind_for_jinja(query)
    return all_compounds


# region auxiliary functions
def extract_ids(qid, wikidata_result):
    ids = {
        "wikidata": {
            "name": "Wikidata ID",
            "symbol": qid,
            "url": f"https://wikidata.org/wiki/{qid}",
        }
    }
    # Note that one "value" comes from Wikidata and the other is the value of the "value" key
    for key, value in wikidata_result.items():

        if key in FORMATTER_DICT:
            if value != "" and "," not in value:
                name = key.replace("_", " ")

                ids[key] = {
                    "name": name,
                    "symbol": value,
                    "url": FORMATTER_DICT[key].replace("$1", value),
                }

    return ids


def get_wikidata_info(query_name, protein_qid):
    """
    Retrieves info from Wikidata based on a query name.
    """

    template = Template(
        QUERIES.joinpath(f"{query_name}.jinja.rq").read_text(encoding="UTF-8")
    )

    query = template.render(protein_qid=protein_qid)

    return query_wikidata(query)


def clean_up_pmids(web_page):
    web_page = re.sub(
        "PubMed:([0-9]*)",
        '<a href="https://pubmed.ncbi.nlm.nih.gov/\\1" target=" _blank">PMID:\\1</a>',
        web_page,
        count=0,
        flags=0,
    )

    return web_page


def get_all_of_a_kind_for_jinja(query):
    all_diseases_df = wikidata2df(query)
    all_diseases = []
    for _, row in all_diseases_df.iterrows():
        all_diseases.append({"name": row["itemLabel"], "id": row["qid"]})
    all_diseases = json.dumps(all_diseases).replace('"name"', "name")
    return all_diseases


def get_protein_result(wikidata_result):
    """ """
    protein_qid = wikidata_result["protein"].split("/")[-1]

    item_json = requests.get(
        f"https://www.wikidata.org/wiki/Special:EntityData/{protein_qid}.json"
    ).json()

    protein_template = Template(
        QUERIES.joinpath("protein_template.jinja.rq").read_text(encoding="UTF-8")
    )

    query = protein_template.render(protein_qid=protein_qid)

    protein_result = query_wikidata(query)[0]

    protein_result["ensembl_ids"] = extract_value_from_wikidata_json(item_json, "P705")

    protein_result["ensembl_ids"] = extract_value_from_wikidata_json(item_json, "P637")

    protein_result["domains"] = get_wikidata_info(
        "domains_and_families", protein_qid=protein_qid
    )
    protein_result["molecular_functions"] = get_wikidata_info(
        "molecular_functions", protein_qid=protein_qid
    )
    protein_result["cell_components"] = get_wikidata_info(
        "cell_components", protein_qid=protein_qid
    )
    protein_result["biological_processes"] = get_wikidata_info(
        "biological_processes", protein_qid=protein_qid
    )
    protein_result["wikipathways"] = get_wikidata_info(
        "wikipathways", protein_qid=protein_qid
    )
    protein_result["reactome_pathways"] = get_wikidata_info(
        "reactome_pathways", protein_qid=protein_qid
    )
    protein_result["protein_complexes"] = get_wikidata_info(
        "protein_complexes", protein_qid=protein_qid
    )
    protein_result["swissbiopics_list"] = ",".join(
        [
            a["Gene_Ontology_ID"].split(":")[-1]
            for a in protein_result["cell_components"]
        ]
    )
    uniprot_info = get_uniprot_info(protein_result["UniProt_protein_ID"])
    protein_result["pdb_ids"] = [
        {"id": id} for id in protein_result["PDB_structure_ID"].split(" | ")
    ]

    return protein_result, uniprot_info
