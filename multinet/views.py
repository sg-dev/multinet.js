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
def sample_data(dataset):
    filename = "%s/%s.csv" % ( VISUALIZATION_DIR, dataset)  
    nd_filename = "%s/%s_node_data.csv" % ( VISUALIZATION_DIR, dataset)
    data = graph_layout(filename, nd_filename) 

    return jsonify(url=url_for('sample_data', dataset=dataset), **data)


@app.route('/uploaded/<dataset>')
def uploaded_graph(dataset):
    data = graph_layout(
        os.path.join(app.config['UPLOAD_FOLDER'], '{}.csv'.format(dataset)),
        os.path.join(app.config['UPLOAD_FOLDER'], '{}_node_data.csv'.format(dataset))
    )
    return jsonify(**data)



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload/', methods=['POST',])
def upload_file():
    edge_file = request.files.get('file', None)
    data_file = request.files.get('nodefile', None)
    if edge_file and allowed_file(edge_file.filename):
        filename = secure_filename(edge_file.filename)
        dataset = filename.rsplit('.', 1)[1]
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        edge_file.save(path)
    else:
        return jsonify(graph_ready=False, errors='Invalid file uploaded. Only .csv files are supported')

    data_path = None
    if data_file and allowed_file(data_file.filename):
        data_path = os.path.join(app.config['UPLOAD_FOLDER'], '{}_node_data.csv')
        data_file.save(data_path)

    data = graph_layout(path, data_path)
    return jsonify(url=url_for('uploaded_graph', dataset=dataset), **data)

