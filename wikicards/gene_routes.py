import json
import re
from io import BytesIO
from pathlib import Path
import requests
from app import app
from flask import redirect, render_template, request
from helper import *
from jinja2 import Template
from PIL import Image
from wdcuration import get_statement_values, query_wikidata

HERE = Path(__file__).parent.resolve()
QUERIES = HERE.joinpath("queries").resolve()
DICTS = HERE.joinpath("dicts").resolve()
FORMATTER_DICT = json.loads(DICTS.joinpath("formatter_dict.json").resolve().read_text())


@app.route("/gene", methods=["GET", "POST"])
def gene():
    if request.method == "POST":
        gene = request.form["gene"]
        return redirect(f"/gene/{gene}")
    all_genes = get_all_genes()
    return render_template("public/gene.html", genes=all_genes)


@app.route("/gene/<gene_id>", methods=["GET", "POST"])
def particular_gene(gene_id):
    gene_template = Template(
        QUERIES.joinpath("gene_template.jinja.rq").read_text(encoding="UTF-8")
    )
    query = gene_template.render(target=gene_id)
    try:
        wikidata_result = query_wikidata(query)[0]
    except IndexError:
        all_genes = get_all_genes()
        return render_template(
            "public/gene.html",
            genes=all_genes,
            gene_not_found_message=f'<div class="alert alert-warning" role="alert">No results found for "{gene_id}", try another.</div>',
        )
    ids = extract_ids(wikidata_result["gene"].split("/")[-1], wikidata_result)
    summaries = {}
    summaries["entrez"] = get_entrez_summary(ids["Entrez_Gene_ID"]["symbol"])
    if "en_wiki_label" in wikidata_result:
        summaries["wikipedia"] = get_wikipedia_summary(wikidata_result["en_wiki_label"])
    protein_result, uniprot_info = get_protein_result(wikidata_result)
    gene_qid = wikidata_result["gene"].split("/")[-1]
    wikidata_result["ensembl_rna_ids"] = get_statement_values(gene_qid, "P704")
    wikidata_result["refseq_rna_ids"] = get_statement_values(gene_qid, "P639")
    stringdb_image = get_string_db_image(gene_id)
    web_page = render_template(
        "public/gene.html",
        wikidata_result=wikidata_result,
        protein_result=protein_result,
        uniprot_info=uniprot_info,
        stringdb_image=stringdb_image,
        ids=ids,
        summaries=summaries,
    )

    web_page = clean_up_pmids(web_page)
    return web_page


def get_string_db_image(gene_id):
    r = requests.get(f"https://string-db.org/api/image/network?identifiers={gene_id}")
    stringdb_image = Image.open(BytesIO(r.content))
    stringdb_image = stringdb_image.convert("RGB")
    stringdb_image = serve_pil_image(stringdb_image)
    return stringdb_image
