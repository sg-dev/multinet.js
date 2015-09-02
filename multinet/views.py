import os

from flask import render_template, jsonify, Flask, request, redirect, url_for

from werkzeug import secure_filename

from multinet import app, VISUALIZATION_DIR
from multinet.render import graph_layout


ALLOWED_EXTENSIONS = set(['csv',])


@app.route('/')
def main():
    return render_template('main.html')


@app.route('/sample/<dataset>')
def sample_visuals_np(dataset):
        filename = "%s/%s.csv" % ( VISUALIZATION_DIR, dataset)  
        nd_filename = "%s/%s_node_data.csv" % ( VISUALIZATION_DIR, dataset)
        data = graph_layout(filename, nd_filename) 

        return jsonify(**data)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload/', methods=['POST',])
def upload_file():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        data = graph_layout(path, None)
        return jsonify(**data)

    return jsonify(error='Invalid fileupload')
