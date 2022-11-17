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
from helper import (
    get_entrez_summary,
    get_uniprot_info,
    get_wikipedia_summary,
    get_uniprot_info,
    serve_pil_image,
)
from wikidata2df import wikidata2df
from wdcuration import get_statement_values, query_wikidata
import re
from PIL import Image
from io import BytesIO


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
        QUERIES.joinpath("cell_template.rq.jinja").read_text(encoding="UTF-8")
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
    summaries["wikipedia"] = get_wikipedia_summary(wikidata_result["en_wiki_label"])

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
        QUERIES.joinpath("compound_template.rq.jinja").read_text(encoding="UTF-8")
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
        QUERIES.joinpath("disease_template.rq.jinja").read_text(encoding="UTF-8")
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
    summaries["wikipedia"] = get_wikipedia_summary(wikidata_result["en_wiki_label"])

    web_page = render_template(
        "public/disease.html",
        wikidata_result=wikidata_result,
        ids=ids,
        summaries=summaries,
    )

    web_page = clean_up_pmids(web_page)
    return web_page


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
        QUERIES.joinpath("gene_template.rq.jinja").read_text(encoding="UTF-8")
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
    summaries["wikipedia"] = get_wikipedia_summary(wikidata_result["en_wiki_label"])

    protein_result, uniprot_info = get_protein_result(wikidata_result)

    gene_qid = wikidata_result["gene"].split("/")[-1]
    wikidata_result["ensembl_rna_ids"] = get_statement_values(gene_qid, "P704")
    wikidata_result["refseq_rna_ids"] = get_statement_values(gene_qid, "P639")

    r = requests.get(f"https://string-db.org/api/image/network?identifiers={gene_id}")

    stringdb_image = Image.open(BytesIO(r.content))
    stringdb_image = stringdb_image.convert("RGB")

    stringdb_image = serve_pil_image(stringdb_image)

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


# endregion

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
        print(key)
        print(value)

        if key in FORMATTER_DICT:
            if value != "" and "," not in value:
                print(key)
                print(value)
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
        QUERIES.joinpath(f"{query_name}.rq.jinja").read_text(encoding="UTF-8")
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

    query = (
        "SELECT DISTINCT ?itemLabel"
        '  (REPLACE(STR(?item), ".*Q", "Q") AS ?qid) '
        " WHERE {?item wdt:P31 wd:Q113681859 .  "
        "?item rdfs:label ?itemLabel . "
        "FILTER (LANG (?itemLabel) = 'en') }"
    )
    all_compounds = get_all_of_a_kind_for_jinja(query)
    return all_compounds


def get_all_of_a_kind_for_jinja(query):
    all_diseases_df = wikidata2df(query)
    all_diseases = []
    for _, row in all_diseases_df.iterrows():
        all_diseases.append({"name": row["itemLabel"], "id": row["qid"]})
    all_diseases = json.dumps(all_diseases).replace('"name"', "name")
    return all_diseases


def get_protein_result(wikidata_result):
    protein_template = Template(
        QUERIES.joinpath("protein_template.rq.jinja").read_text(encoding="UTF-8")
    )
    protein_qid = wikidata_result["protein"].split("/")[-1]

    query = protein_template.render(protein_qid=protein_qid)

    protein_result = query_wikidata(query)[0]

    protein_result["ensembl_ids"] = get_statement_values(protein_qid, "P705")
    protein_result["refseq_ids"] = get_statement_values(protein_qid, "P637")

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


# endregion
