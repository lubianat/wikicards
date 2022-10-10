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
from helper import get_entrez_summary, get_wikipedia_summary


HERE = Path(__file__).parent.resolve()
QUERIES = HERE.joinpath("queries").resolve()
DICTS = HERE.joinpath("dicts").resolve()
FORMATTER_DICT = json.loads(DICTS.joinpath("formatter_dict.json").resolve().read_text())


app = Flask(__name__)


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route("/gene/")
def gene():

    return render_template("public/gene.html")


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
    return render_template(
        "public/gene.html",
        wikidata_result=wikidata_result,
        ids=ids,
        summaries=summaries,
    )
