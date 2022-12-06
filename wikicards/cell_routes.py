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


@app.route("/cell", methods=["GET", "POST"])
def cell():
    if request.method == "POST":
        cell = request.form["cell"]
        return redirect(f"/cell/{cell}")
    all_cells = get_all_cells()
    return render_template("public/cell.html", cells=all_cells)


@app.route("/cell/<cell_qid>", methods=["GET", "POST"])
def particular_cell(cell_qid):

    cell_template = Template(
        QUERIES.joinpath("cell_template.jinja.rq").read_text(encoding="UTF-8")
    )
    query = cell_template.render(target=cell_qid)

    try:
        wikidata_result = query_wikidata(query)[0]
    except IndexError:
        all_cells = get_all_cells()

        return render_template(
            "public/cell.html",
            cells=all_cells,
            cell_not_found_message=f'<div class="alert alert-warning" role="alert">No results found", try another.</div>',
        )
    ids = extract_ids(cell_qid, wikidata_result)

    summaries = {}
    if "en_wiki_label" in wikidata_result:
        wikipedia_data = get_wikipedia_summary(wikidata_result["en_wiki_label"])

        if "originalimage" not in wikipedia_data:
            wikipedia_data["originalimage"] = {}
            wikipedia_data["originalimage"]["source"] = ""
            app.logger.warning("%s has no image", wikidata_result["en_wiki_label"])

        summaries["wikipedia"] = wikipedia_data
    summaries["cell_ontology"] = get_ontological_definition(
        ids["Cell_Ontology_ID"]["symbol"]
    )
    web_page = render_template(
        "public/cell.html",
        wikidata_result=wikidata_result,
        ids=ids,
        summaries=summaries,
    )

    web_page = clean_up_pmids(web_page)
    return web_page
