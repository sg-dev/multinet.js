from flask import render_template
from flask import jsonify

from sgvisuals import app, VISUALIZATION_DIR
from sgvisuals.render import graph_layout


@app.route('/')
def main():
    return render_template('main.html')


@app.route('/sample/<dataset>')
def sample_visuals_np(dataset):
        filename = "%s/%s.csv" % ( VISUALIZATION_DIR, dataset)  
        nd_filename = "%s/%s_node_data.csv" % ( VISUALIZATION_DIR, dataset)
        data = graph_layout(filename, nd_filename, True) 

        return jsonify(**data)
