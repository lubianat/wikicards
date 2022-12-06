from flask import Flask, render_template
from flask.logging import default_handler


app = Flask(__name__)


@app.route("/")
def hello_world():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


from wikicards.disease_routes import *
from wikicards.gene_routes import *
from wikicards.cell_routes import *
from wikicards.compound_routes import *
