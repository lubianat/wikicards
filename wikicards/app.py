from typing import OrderedDict
from flask import (
    Flask,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from jinja2 import Template
from pathlib import Path
import urllib
import requests
import json
from helper import get_entrez_summary, get_wikipedia_summary, get_uniprot_isoforms
from wikidata2df import wikidata2df

HERE = Path(__file__).parent.resolve()
QUERIES = HERE.joinpath("queries").resolve()
DICTS = HERE.joinpath("dicts").resolve()
FORMATTER_DICT = json.loads(DICTS.joinpath("formatter_dict.json").resolve().read_text())


app = Flask(__name__)


@app.route("/")
def hello_world():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/gene", methods=["GET", "POST"])
def gene():
    if request.method == "POST":
        print(request.form)
        gene = request.form["gene"]
        return redirect(f"/gene/{gene}")

    all_genes_df = wikidata2df(
        "SELECT DISTINCT ?HGNC_gene_symbol WHERE {?item wdt:P353 ?HGNC_gene_symbol}"
    )
    all_genes = []
    for gene in all_genes_df["HGNC_gene_symbol"]:
        all_genes.append({"name": gene})
    all_genes = json.dumps(all_genes).replace('"name"', "name")
    all_genes = all_genes.replace('"', "'")

    return render_template("public/gene.html", genes=all_genes)


@app.route("/gene/<gene_id>", methods=["GET", "POST"])
def search_with_topic(gene_id):

    gene_template = Template(
        QUERIES.joinpath("gene_template.rq.jinja").read_text(encoding="UTF-8")
    )
    query = gene_template.render(target=gene_id)

    try:
        response = requests.get(
            url="https://query.wikidata.org/sparql",
            params={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()

    except requests.exceptions.HTTPError as err:
        raise requests.exceptions.HTTPError(err)
    wikidata_result = response.json()["results"]["bindings"][0]
    print(wikidata_result)

    ids = {
        "wikidata": {
            "name": "Wikidata ID",
            "symbol": wikidata_result["gene"]["value"].split("/")[-1],
            "url": wikidata_result["gene"]["value"],
        }
    }
    # Note that one "value" comes from Wikidata and the other is the value of the "value" key
    for key, value in wikidata_result.items():
        if key in FORMATTER_DICT:
            if value["value"] != "" and "," not in value["value"]:
                name = key.replace("_", " ")

                ids[key] = {
                    "name": name,
                    "symbol": value["value"],
                    "url": FORMATTER_DICT[key].replace("$1", value["value"]),
                }

    summaries = {}
    summaries["entrez"] = get_entrez_summary(ids["Entrez_Gene_ID"]["symbol"])
    summaries["wikipedia"] = get_wikipedia_summary(
        wikidata_result["en_wiki_label"]["value"]
    )

    protein_template = Template(
        QUERIES.joinpath("protein_template.rq.jinja").read_text(encoding="UTF-8")
    )
    query = protein_template.render(
        protein_qid=wikidata_result["protein"]["value"].split("/")[-1]
    )

    try:
        response = requests.get(
            url="https://query.wikidata.org/sparql",
            params={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
        response.raise_for_status()

    except requests.exceptions.HTTPError as err:
        raise requests.exceptions.HTTPError(err)
    protein_result = response.json()["results"]["bindings"][0]
    uniprot_isoforms = get_uniprot_isoforms(
        protein_result["UniProt_protein_ID"]["value"]
    )
    protein_result["isoforms"] = uniprot_isoforms
    protein_result["pdb_ids"] = [
        {"id": id} for id in protein_result["PDB_structure_ID"]["value"].split(" | ")
    ]
    protein_result["ensembl_ids"] = [
        {"id": id} for id in protein_result["Ensembl_protein_ID"]["value"].split(" | ")
    ]
    protein_result["refseq_ids"] = [
        {"id": id} for id in protein_result["RefSeq protein ID"]["value"].split(" | ")
    ]

    return render_template(
        "public/gene.html",
        wikidata_result=wikidata_result,
        protein_result=protein_result,
        ids=ids,
        summaries=summaries,
    )
