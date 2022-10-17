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
from wdcuration import get_statement_values, query_wikidata

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

    wikidata_result = query_wikidata(query)[0]

    ids = {
        "wikidata": {
            "name": "Wikidata ID",
            "symbol": wikidata_result["gene"].split("/")[-1],
            "url": wikidata_result["gene"],
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

    summaries = {}
    summaries["entrez"] = get_entrez_summary(ids["Entrez_Gene_ID"]["symbol"])
    summaries["wikipedia"] = get_wikipedia_summary(wikidata_result["en_wiki_label"])

    protein_template = Template(
        QUERIES.joinpath("protein_template.rq.jinja").read_text(encoding="UTF-8")
    )
    protein_qid = wikidata_result["protein"].split("/")[-1]
    query = protein_template.render(protein_qid=protein_qid)

    protein_result = query_wikidata(query)[0]
    uniprot_isoforms = get_uniprot_isoforms(protein_result["UniProt_protein_ID"])
    protein_result["isoforms"] = uniprot_isoforms
    protein_result["pdb_ids"] = [
        {"id": id} for id in protein_result["PDB_structure_ID"].split(" | ")
    ]
    protein_result["ensembl_ids"] = get_statement_values(protein_qid, "P705")
    protein_result["refseq_ids"] = get_statement_values(protein_qid, "P637")

    return render_template(
        "public/gene.html",
        wikidata_result=wikidata_result,
        protein_result=protein_result,
        ids=ids,
        summaries=summaries,
    )
