import json
import re
from io import BytesIO
from pathlib import Path
import requests
from wikicards.app import app
from flask import redirect, render_template, request
from .helper import *
from jinja2 import Template
from PIL import Image
from wdcuration import get_statement_values, query_wikidata

HERE = Path(__file__).parent.resolve()
QUERIES = HERE.joinpath("queries").resolve()
DICTS = HERE.joinpath("dicts").resolve()
FORMATTER_DICT = json.loads(DICTS.joinpath("formatter_dict.json").resolve().read_text())


@app.route("/disease", methods=["GET", "POST"])
def disease():
    if request.method == "POST":
        disease = request.form["disease"]
        return redirect(f"/disease/{disease}")
    all_diseases = get_all_diseases()
    return render_template("public/disease.html", diseases=all_diseases)


@app.route("/disease/<disease_qid>", methods=["GET", "POST"])
def particular_disease(disease_qid):

    disease_template = Template(
        QUERIES.joinpath("disease_template.jinja.rq").read_text(encoding="UTF-8")
    )
    query = disease_template.render(target=disease_qid)

    try:
        wikidata_result = query_wikidata(query)[0]
    except IndexError:
        all_diseases = get_all_diseases()

        return render_template(
            "public/disease.html",
            diseases=all_diseases,
            disease_not_found_message=f'<div class="alert alert-warning" role="alert">No results found", try another.</div>',
        )
    ids = extract_ids(disease_qid, wikidata_result)

    summaries = {}
    if "en_wiki_label" in wikidata_result:
        summaries["wikipedia"] = get_wikipedia_summary(wikidata_result["en_wiki_label"])

    if "Disease_Ontology_ID" in wikidata_result:
        summaries["disease_ontology"] = get_ontological_definition(
            ids["Disease_Ontology_ID"]["symbol"]
        )
    if "MonDO_ID" in ids:
        summaries["mondo"] = get_ontological_definition(ids["MonDO_ID"]["symbol"])
    web_page = render_template(
        "public/disease.html",
        wikidata_result=wikidata_result,
        ids=ids,
        summaries=summaries,
    )

    web_page = clean_up_pmids(web_page)
    return web_page
