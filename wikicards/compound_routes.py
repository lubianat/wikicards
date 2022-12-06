import json
import re
from io import BytesIO
from pathlib import Path
import requests
from app import app
from flask import redirect, render_template, request
from .helper import *
from jinja2 import Template
from PIL import Image
from wdcuration import get_statement_values, query_wikidata

HERE = Path(__file__).parent.resolve()
QUERIES = HERE.joinpath("queries").resolve()
DICTS = HERE.joinpath("dicts").resolve()
FORMATTER_DICT = json.loads(DICTS.joinpath("formatter_dict.json").resolve().read_text())


@app.route("/compound", methods=["GET", "POST"])
def compound():
    if request.method == "POST":
        compound = request.form["compound"]
        return redirect(f"/compound/{compound}")
    all_compounds = get_all_compounds()
    return render_template("public/compound.html", compounds=all_compounds)


@app.route("/compound/<compound_qid>", methods=["GET", "POST"])
def particular_compound(compound_qid):

    compound_template = Template(
        QUERIES.joinpath("compound_template.jinja.rq").read_text(encoding="UTF-8")
    )
    query = compound_template.render(target=compound_qid)

    try:
        wikidata_result = query_wikidata(query)[0]
    except IndexError:
        all_compounds = get_all_compounds()

        return render_template(
            "public/compound.html",
            compounds=all_compounds,
            compound_not_found_message=f'<div class="alert alert-warning" role="alert">No results found", try another.</div>',
        )
    ids = extract_ids(compound_qid, wikidata_result)

    summaries = {}
    summaries["wikipedia"] = get_wikipedia_summary(wikidata_result["en_wiki_label"])

    web_page = render_template(
        "public/compound.html",
        wikidata_result=wikidata_result,
        ids=ids,
        summaries=summaries,
    )

    web_page = clean_up_pmids(web_page)
    return web_page
