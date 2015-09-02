import os
import hashlib

from flask import render_template, jsonify, Flask, request, redirect, url_for

from werkzeug import secure_filename

from multinet import app, VISUALIZATION_DIR
from multinet.render import graph_layout, get_hash


ALLOWED_EXTENSIONS = set(['csv',])


@app.route('/')
def main():
    return render_template('main.html')


@app.route('/share/<dataset>/')
@app.route('/share/<dataset>/<hash>/')
def share(dataset, hash=None):
    return render_template('main.html', fetch_url=url_for('data', dataset=dataset, hash=hash))


@app.route('/data/<dataset>/')
@app.route('/data/<dataset>/<hash>/')
def data(dataset, hash=None):
    if hash:
        base_path = app.config['UPLOAD_FOLDER']
        dataset = '{}_{}'.format(dataset, hash)
    else:
        base_path = VISUALIZATION_DIR

    data = graph_layout(
        os.path.join(base_path, '{}.csv'.format(dataset)),
        os.path.join(base_path, '{}_node_data.csv'.format(dataset))
    )

    return jsonify(url=url_for('share', dataset=dataset, hash=hash), **data)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload/', methods=['POST',])
def upload_file():
    edge_file = request.files.get('file', None)
    data_file = request.files.get('nodefile', None)
    if edge_file and allowed_file(edge_file.filename):
        filename = secure_filename(edge_file.filename)
        hasher = hashlib.md5()
        hasher.update(edge_file.stream.read())
        hash = hasher.hexdigest()
        dataset = filename.rsplit('.', 1)[0]
        filename = '{}_{}.csv'.format(dataset, hash)
        edge_file.stream.seek(0)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        edge_file.save(path)
    else:
        return jsonify(graph_ready=False, errors='Invalid file uploaded. Only .csv files are supported')

    data_path = None
    if data_file and allowed_file(data_file.filename):
        data_path = os.path.join(app.config['UPLOAD_FOLDER'], '{}_{}_node_data.csv'.format(dataset, hash))
        data_file.save(data_path)

    data = graph_layout(path, data_path)
    return jsonify(url=url_for('share', dataset=dataset, hash=hash), **data)

