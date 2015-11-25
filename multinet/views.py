# Copyright (c) 2015, ETH Zurich, Chair of Systems Design
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import hashlib

from flask import render_template, jsonify, Flask, request, redirect, url_for

from werkzeug import secure_filename

from multinet import app, VISUALIZATION_DIR
import multinet.render
from multinet.render import graph_layout


ALLOWED_EXTENSIONS = set(['csv',])

TIMEFORMAT = "%Y-%m-%d %H:%M:%S"

import sys, traceback
import random
import string
from datetime import datetime, timedelta


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

    #if app.config['USE_CELERY']
    data = graph_layout(
        os.path.join(base_path, '{}.csv'.format(dataset)),
        os.path.join(base_path, '{}_node_data.csv'.format(dataset))
    )

    if "errors" in data.keys():
        return jsonify(graph_ready=False, errors=data["errors"])
    
    return jsonify(url=url_for('share', dataset=dataset, hash=hash), **data)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload/', methods=['POST',])
def upload_file():
    
    #check if client reached quota
    if not check_quota():
        return jsonify(graph_ready=False, errors="Quota Reached. You can upload one edgelist every 10 minutes.")
        
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
        ret = insert_file(path)
    else:
        return jsonify(graph_ready=False, errors='Invalid file uploaded. Only .csv files are supported')

    data_path = None
    if data_file and allowed_file(data_file.filename):
        data_path = os.path.join(app.config['UPLOAD_FOLDER'], '{}_{}_node_data.csv'.format(dataset, hash))
        data_file.save(data_path)

    layout_algorithm = request.form.get('layout_algorithm', 'Fruchterman-Reingold')
    data = graph_layout(path, data_path, directed_graph=request.form.get('is_directed', 'true')=='true', ly_alg=layout_algorithm)
    
    #print "dat",data
    if "errors" in data.keys():
        print "ERRORS",data["errors"]
        return jsonify(graph_ready=False, errors=data["errors"])
    
    return jsonify(url=url_for('share', dataset=dataset, hash=hash), **data)

