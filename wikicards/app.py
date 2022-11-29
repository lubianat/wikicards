import json
import re
import urllib
from io import BytesIO
from logging.config import dictConfig
from pathlib import Path
from typing import OrderedDict

import requests
from flask import (Flask, current_app, flash, redirect, render_template,
                   request, url_for)
from flask.logging import default_handler
from helper import (extract_value_from_wikidata_json, get_all_cells,
                    get_all_compounds, get_all_diseases, get_entrez_summary,
                    get_ontological_definition, get_uniprot_info,
                    get_wikipedia_summary, serve_pil_image)
from jinja2 import Template
from PIL import Image
from wdcuration import get_statement_values, query_wikidata
from wikidata2df import wikidata2df

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            },
            "file": {
                "class": "logging.FileHandler",
                "filename": "flask.log",
                "formatter": "default",
            },
        },
        "root": {"level": "WARNING", "handlers": ["console", "file"]},
    }
)


HERE = Path(__file__).parent.resolve()
QUERIES = HERE.joinpath("queries").resolve()
DICTS = HERE.joinpath("dicts").resolve()
FORMATTER_DICT = json.loads(DICTS.joinpath("formatter_dict.json").resolve().read_text())


app = Flask(__name__)

# region app and routes
@app.route("/")
def hello_world():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


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


import gene_routes

# endregion


# endregion
