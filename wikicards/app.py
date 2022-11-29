from flask import Flask, render_template
from flask.logging import default_handler


app = Flask(__name__)


@app.route("/")
def hello_world():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


import disease_routes
import gene_routes
import cell_routes
import compound_routes
