import os

from flask import Flask


app = Flask(__name__)

VISUALIZATION_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static/graph-samples'
)


import sgvisuals.views
