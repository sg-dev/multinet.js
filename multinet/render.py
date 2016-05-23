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

import csv
import matplotlib.mlab
import numpy as np
import cPickle
import hashlib
import igraph
import collections
import string
import random
import base64
import math
import fastlayout as fl

from datetime import datetime
from itertools import groupby

from multinet import VISUALIZATION_DIR

import celery

from flask import jsonify, render_template
    

SUPPORTED_LAYOUTS = ['Fruchterman-Reingold','Kamada-Kawai', 'LGL', 'Random', 'Star']
CACHE_PATH_TEMPLATE = '/tmp/multinet_{}.cpickle'


def generate_id(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def get_hash(path, options):
    hasher = hashlib.md5()

    with open(path) as f:
        hasher.update(f.read())
        hasher.update(str(options))
        return hasher.hexdigest()


def get_cache_path(path, options):
    return CACHE_PATH_TEMPLATE.format(get_hash(path, options))


def get_from_cache(path, options):
    try:
        with open(get_cache_path(path, options), 'rb') as f:
            return cPickle.load(f)
    except:
        return None


def cache_data(path, data, options):
    with open(get_cache_path(path, options), 'wb') as f:
        cPickle.dump(data, f, protocol=2)

class MultiGraph:
    def __init__(self):
        self.igraph = igraph.Graph()
        self.layer_names = []
        self.data = {} 
        self.max_node_ct = 0
        self.unique_keys = ['00-00-0000']
        self.node_data = {}
        self.data_labels = []
        self.custom_scale = {}

    def add_layer(self, layer_name):
        if layer_name not in self.layer_names:
            self.layer_names.append(layer_name)
            self.data[layer_name] = {
                'edges': [],
                'nodes': [],
                'edge_ct': 0,
                'node_ct': 0,
                'in_degrees': {},
                'out_degrees': {}
            }

    def add_edge(self, from_, to, layer):
        self.igraph.add_vertices([from_, to])
        self.igraph.add_edge(from_, to)
        layer_data = self.data[layer]
        layer_data['edges'].append([from_, to, "00-00-0000"])
        layer_data['nodes'] = list(set(layer_data['nodes'] + [from_, to]))
        self.max_node_ct = max(self.max_node_ct, len(layer_data['nodes']))

    def layout(self, ly_alg = "Fruchterman-Reingold", directed_graph=True):

        if ly_alg not in SUPPORTED_LAYOUTS:
            return {
                "graph_ready": False,
                "errors": "Unsuspported layout algorithm"
            }

        print "VIZUALISATION TIMER: igraph layouting :",datetime.now() 
        ly_start = datetime.now()

        #new layouting by rcattano
        dimension = 2
        max_it = 500
        temp = 1
        nodes = len(self.igraph.vs)
        edges = np.array( [edge.tuple for edge in self.igraph.es], np.int32)

        _l = len(edges)

        pos = fl.layout_fr(nodes*dimension, edges, max_it, temp )

        #get the Layout object here. 
        #http://igraph.org/python/doc/igraph.layout.Layout-class.html
        scl =  int( _l/ 100 ) #int( _l * _l / 10 )
        if ly_alg == "Fruchterman-Reingold":
            ly = igraph.Layout(tuple(zip(pos[0:nodes], pos[nodes:2*nodes])))
            scl = scl / 3
        elif ly_alg == "LGL":
            ly = self.igraph.layout_lgl()
        elif ly_alg == "Kamada-Kawai":
            ly = self.igraph.layout_kamada_kawai()
            scl = scl / 10
        elif ly_alg == "Star":
            ly = self.igraph.layout_star()
            scl =  scl * 2
        elif ly_alg == "Random":
            ly = self.igraph.layout_random()
            scl =  scl * 2
        else:
            #ly = igraph.Layout( tuple(map(tuple, pos )) )
            #scl = scl / 3
            ly = self.igraph.layout_fruchterman_reingold(dim=2,coolexp =1, area = int( _l * _l / 10 ) )
            #ly_alg = "Fruchterman-Reingold"
            #OR standard fruchterman reingold
            
        ly_end = datetime.now()
        diff = ly_end - ly_start

        print "VIZUALISATION TIMER: returning coordinates :",ly_end
        print "Layouting took :", diff.seconds, "seconds using", ly_alg 

        # TODO screws up positioning for graphs with few nodes
        #ly.scale( scl * 4)

        box = ly.bounding_box()
        width = abs(box.left) + abs(box.right)

        coords = ly.__dict__['_coords']
        #numpy.float64 cannot be jsonified later, so we convert to standard float:
        coords = [ [ float( c[0] )* 1 , float( c[1] ) * 1 ] for c in coords  ]

        #todo we have the node names somewhere already ...
        vertices = []
        for i in self.igraph.vs:
            vertices.append( i['name'] )

        all_coords = dict( zip( vertices, coords ) )

        #add coords to each layer and get the nodes in each layer intersect with the nodes in the next layer
        layer_neighborhoods = []
        for i,_l in enumerate(self.layer_names):
            _layer_data = self.data[_l]

            _layer_data['name'] = _l

            try:
                _layer_data_next = data[ self.layer_names[i+1] ]
            except:
                #last layer
                _layer_data_next = self.data[ self.layer_names[i-1] ]

            #possible with namedtuples
            #nodes1 = _layer_data.nodes
            #nodes2 = _layer_data_next.nodes
            #indegs = _layer_data.in_degrees
            max_in_deg = 0
            max_out_deg = 0
            max_total_deg = 0
            nodes1 = _layer_data['nodes']
            nodes2 = _layer_data_next['nodes']
            indegs = _layer_data['in_degrees']
            outdegs = _layer_data['out_degrees']

            coords = {}
            common_nodes = list(  set( nodes1 ).intersection( set( nodes2 ) ) )

            for node_id in nodes1:
                _common = 1 if node_id in common_nodes else 0
                try:
                    indeg = indegs[ node_id ]
                    outdeg = outdegs[ node_id ]
                except Exception,e:
                    indeg = 0
                    outdeg = 0
                coords[node_id] = [ all_coords[ node_id ], _common, indeg, outdeg, indeg + outdeg, self.custom_scale.get(node_id, 1)] 

                max_out_deg = max(max_out_deg, outdeg)
                max_in_deg = max(max_in_deg, indeg)
                max_total_deg = max(max_total_deg, outdeg + indeg)
            #possible with namedtuples
            #_layer_data.coords = coords

            _layer_data['coords'] = coords

            # add dummy 0 values, so max_in_degree and max_out_degree have to 
            # same offset as the node's degrees
            _layer_data['maxDeg'] = [0, 0, max_in_deg, max_out_deg, max_total_deg, 1.0] 

            if directed_graph:
                get_key = lambda v1, v2: ''.join([v1, v2])
            else:
                get_key = lambda v1, v2: ''.join(sorted([v1, v2]))

            edge_dict = { get_key(x[0], x[1]):  x[2] for x in _layer_data['edges']}

            neighborhood = {}
            for i, nb in enumerate(self.igraph.neighborhood()):
                l = []
                neighborhood[vertices[i]] = neighborhood.get(vertices[i], l)  + [[vertices[j], edge_dict[get_key(vertices[i], vertices[j])]] for j in nb if get_key(vertices[i], vertices[j]) in edge_dict]
            _layer_data['neighborhood'] = neighborhood

        print "VIZUALISATION TIMER: returning response to frontend :",datetime.now() 

        data = self.data 
        data['layer_ct'] = len(self.data)
        data['max_node_ct'] = self.max_node_ct
        data['unique_keys'] = self.unique_keys
        data['width'] = width
        data['layout'] = ly_alg
        data['layers'] = [self.data[l] for l in sorted(self.layer_names)]
        if len(self.node_data) == 0 :
            data['node_data'] = { n: [] for n in set(sum([self.data[l]['nodes'] for l in sorted(self.layer_names)], [])) }
        else:
            data['node_data'] = self.node_data
        data['data_labels']= self.data_labels
        data['directed'] = directed_graph
        try:
            data['custom_scale'] = self.data_labels.index('scale') > 0
        except:
            data['custom_scale'] = False

        return data

#@celery.task
def graph_layout(filename, node_data_filename, ly_alg = "Fruchterman-Reingold", directed_graph=True):

    if ly_alg not in SUPPORTED_LAYOUTS:
        return {
            "graph_ready": False,
            "errors": "Unsuspported layout algorithm"
        }

    options = {
        'node_data_filename': node_data_filename,
        'ly_algorithm': ly_alg,
        'directed_graph': directed_graph
    }

    cached_data = get_from_cache(filename, options)

    if cached_data:
        return cached_data

    #read the uploaded file 
    _path = filename

    if node_data_filename:
        _nd_path = node_data_filename
    else:
        _nd_path = None

    max_node_ct = 0

    unique_ct = lambda arg1: len(set(arg1))  

    #dictionary to hold all data for each layer:
    data = collections.OrderedDict()

    #data type declaration for edges to be stored in numpy array
    edges_type = [ ('from', np.str_,64), ('to', np.str_,64), ('layer', np.str_,64 ), ('timestamp', np.str_,10 ) ] 

    data_labels = []
    node_data = {}
    custom_scale = {}
    scale_index = -1

    try:

        if _nd_path:
            with open(_nd_path) as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                data_labels = reader.next()
                if 'scale' in data_labels:
                    scale_index = data_labels.index('scale')

                for row in reader:
                    if scale_index > 0:
                        custom_scale[row[0]] = min(max(float(row[scale_index]), 0.0), 1.0)
                    else:
                    node_data[row[0]] = row[1:]


    except Exception,e:
        pass
    
    try:
        with open(_path) as f:
            reader = csv.reader(f, delimiter=';')
            if len(reader.next()) == 3:
                edges_type = edges_type[:3]
        edges = np.loadtxt( open(_path, 'rb'), delimiter=';',  skiprows = 1, dtype = edges_type )
        if len(edges_type) == 3:
            #fill the timestamp column with null timestamps if it is not in data
            timestamps = len(edges["layer"]) * ['00-00-0000']
        else:
            timestamps = edges["timestamp"]
        layers = sorted([ "%s" % ( layer, ) for layer in set( edges["layer"] ) ])

        unique_keys = sorted( list( set(  timestamps ) ) ) 

        print(layers)

        if len(unique_keys) < 100:
            nrbins = len(unique_keys)
        else:
            #shrink keyspace here by order of 10 so that we have less timestamps to deal with.
            nrbins = int( math.floor( len(unique_keys)/10 ) )

        bins = np.linspace(1, len(unique_keys), nrbins)

        keys_indices = dict( zip( unique_keys,  [ i for i in range(1,len(unique_keys) + 1 ) ] ) )
        timestamp_indices =  [ keys_indices[_ts] for _ts in timestamps ]

        #detect which timestamps to be replaced according to the binned indices array
        new_indices = np.digitize( timestamp_indices,bins )
        indices_keys = dict(  zip( new_indices, timestamps ) )
        keys_indices = dict(  zip( timestamps, new_indices ) )

        keys_replace = {}

        for _ind, _ts in enumerate( timestamps ):
            try:
                _key = keys_indices[_ts] 
                _replace_ts = indices_keys[_key] 
                keys_replace[_ind] = _replace_ts
            except Exception,e:
                print e

        for _ind,_replace_ts in keys_replace.iteritems():
            timestamps[_ind] = _replace_ts

        #now we have 10% of the initial keys ..
        unique_keys = sorted( list( set(  timestamps ) ) )

        for layer in layers:
            _layer_data = {}

            edges_tmp = edges[edges["layer"] == layer]

            if len(edges_type) == 3:
                timestamps_tmp = len(edges_tmp["layer"]) * ['00-00-0000']
            else:
                timestamps_tmp = edges_tmp["timestamp"]

            _edges = np.column_stack( ( edges_tmp["from"], edges_tmp["to"], timestamps_tmp ) ).tolist()
            _in_degrees = dict( matplotlib.mlab.rec_groupby(edges_tmp, ('to',), (('from', unique_ct ,'indeg'),)) )
            _nodes = np.append( edges_tmp["from"], edges_tmp["to"]  ).tolist() 
            _out_degrees = {n: len(list(group)) for n, group in groupby(sorted(edges_tmp["from"]))}

            #only possible with namedtuple:
            #_layer_data.edges = _edges
            #_layer_data.nodes = _nodes
            #_layer_data.edge_ct = len(_edges)
            #_layer_data.node_ct = len(_nodes)
            #_layer_data.in_degrees = _in_degrees

            _layer_data['edges'] = _edges
            _layer_data['nodes'] = _nodes
            _layer_data['edge_ct'] = len(_edges)
            _layer_data['node_ct'] = len(_nodes)
            _layer_data['in_degrees'] = _in_degrees
            _layer_data['out_degrees'] = _out_degrees

            max_node_ct = max(max_node_ct, len(_nodes))
            data[layer] = _layer_data

    except Exception,e:
        print "graph init failed 1", _path, e
        return { "graph_ready": False,  "errors": e } #"Improper file format. Please make sure your csv file complies with the tool's format" }

    try:
        #write edges to file
        fid = generate_id()
        tmp_name = "/tmp/edges%s" % (fid,)
        _edges = np.column_stack( ( edges["from"], edges["to"] ) )
        np.savetxt( tmp_name, _edges, fmt="%s", delimiter=' ' )

        _l = len(edges)

        #calculate node coords
        print "VIZUALISATION TIMER: igraph layouting :",datetime.now() 
        #read from tmp file
        ly_start = datetime.now()
        graph = igraph.Graph.Read( tmp_name , directed=directed_graph,format="ncol",weights=False )

        #new layouting by rcattano
        dimension = 2
        max_it = 500
        temp = 1
        nodes = len(graph.vs)
        edges = np.array( [edge.tuple for edge in graph.es], np.int32)

        pos = fl.layout_fr(nodes*dimension, edges, max_it, temp )

        #get the Layout object here. 
        #http://igraph.org/python/doc/igraph.layout.Layout-class.html
        scl =  int( _l/ 100 ) #int( _l * _l / 10 )
        if ly_alg == "Fruchterman-Reingold":
            ly = igraph.Layout(tuple(zip(pos[0:nodes], pos[nodes:2*nodes])))
            scl = scl / 3
        elif ly_alg == "LGL":
            ly = graph.layout_lgl()
        elif ly_alg == "Kamada-Kawai":
            ly = graph.layout_kamada_kawai()
            scl = scl / 10
        elif ly_alg == "Star":
            ly = graph.layout_star()
            scl =  scl * 2
        elif ly_alg == "Random":
            ly = graph.layout_random()
            scl =  scl * 2
        else:
            #ly = igraph.Layout( tuple(map(tuple, pos )) )
            #scl = scl / 3
            ly = graph.layout_fruchterman_reingold(dim=2,coolexp =1, area = int( _l * _l / 10 ) )
            #ly_alg = "Fruchterman-Reingold"
            #OR standard fruchterman reingold
            
        ly_end = datetime.now()
        diff = ly_end - ly_start

        print "VIZUALISATION TIMER: returning coordinates :",ly_end
        print "Layouting took :", diff.seconds, "seconds using", ly_alg 

        ly.scale( scl * 4)

        box = ly.bounding_box()
        width = abs(box.left) + abs(box.right)

        coords = ly.__dict__['_coords']
        #numpy.float64 cannot be jsonified later, so we convert to standard float:
        coords = [ [ float( c[0] )* 1 , float( c[1] ) * 1 ] for c in coords  ]

        #todo we have the node names somewhere already ...
        vertices = []
        for i in graph.vs:
            vertices.append( i['name'] )

        all_coords = dict( zip( vertices, coords ) )

        #add coords to each layer and get the nodes in each layer intersect with the nodes in the next layer
        layer_neighborhoods = []
        for i,_l in enumerate(layers):
            _layer_data = data[_l]

            _layer_data['name'] = _l

            try:
                _layer_data_next = data[ layers[i+1] ]
            except:
                #last layer
                _layer_data_next = data[ layers[i-1] ]

            #possible with namedtuples
            #nodes1 = _layer_data.nodes
            #nodes2 = _layer_data_next.nodes
            #indegs = _layer_data.in_degrees
            max_in_deg = 0
            max_out_deg = 0
            max_total_deg = 0
            nodes1 = _layer_data['nodes']
            nodes2 = _layer_data_next['nodes']
            indegs = _layer_data['in_degrees']
            outdegs = _layer_data['out_degrees']

            coords = {}
            common_nodes = list(  set( nodes1 ).intersection( set( nodes2 ) ) )

            for node_id in nodes1:
                _common = 1 if node_id in common_nodes else 0
                try:
                    indeg = indegs[ node_id ]
                    outdeg = outdegs[ node_id ]
                except Exception,e:
                    indeg = 0
                    outdeg = 0
                coords[node_id] = [ all_coords[ node_id ], _common, indeg, outdeg, indeg + outdeg, custom_scale.get(node_id, 1)] 

                max_out_deg = max(max_out_deg, outdeg)
                max_in_deg = max(max_in_deg, indeg)
                max_total_deg = max(max_total_deg, outdeg + indeg)
            #possible with namedtuples
            #_layer_data.coords = coords

            _layer_data['coords'] = coords

            # add dummy 0 values, so max_in_degree and max_out_degree have to 
            # same offset as the node's degrees
            _layer_data['maxDeg'] = [0, 0, max_in_deg, max_out_deg, max_total_deg, 1.0] 

            if directed_graph:
                get_key = lambda v1, v2: ''.join([v1, v2])
            else:
                get_key = lambda v1, v2: ''.join(sorted([v1, v2]))

            edge_dict = { get_key(x[0], x[1]):  x[2] for x in _layer_data['edges']}

            neighborhood = {}
            for i, nb in enumerate(graph.neighborhood()):
                neighborhood[vertices[i]] = [[vertices[j], edge_dict[get_key(vertices[i], vertices[j])]] for j in nb if get_key(vertices[i], vertices[j]) in edge_dict]
            _layer_data['neighborhood'] = neighborhood

        print "VIZUALISATION TIMER: returning response to frontend :",datetime.now() 

        sd = data
        data = {}
        data['layer_ct'] = len(sd)
        data['max_node_ct'] = max_node_ct
        data['unique_keys'] = unique_keys
        data['width'] = width
        data['layout'] = ly_alg
        data['layers'] = [sd[l] for l in sorted(layers)]
        if len(node_data) == 0 :
            data['node_data'] = { n: [] for n in set(sum([sd[l]['nodes'] for l in sorted(layers)], [])) }
        else:
            data['node_data'] = node_data
        data['data_labels']= data_labels
        data['directed'] = directed_graph
        data['custom_scale'] = scale_index > 0

        data = dict(data)

        cache_data(filename, data, options)

        return data

    except Exception,e:
        print "graph rendering failed", e
        return { "graph_ready": False,  "errors": e, }

def csv_to_multigraph(filename, node_data_filename, directed_graph=True):
    #read the uploaded file 
    _path = filename

    if node_data_filename:
        _nd_path = node_data_filename
    else:
        _nd_path = None

    max_node_ct = 0

    unique_ct = lambda arg1: len(set(arg1))  

    #dictionary to hold all data for each layer:
    data = collections.OrderedDict()

    #data type declaration for edges to be stored in numpy array
    edges_type = [ ('from', np.str_,64), ('to', np.str_,64), ('layer', np.str_,64 ), ('timestamp', np.str_,10 ) ] 

    data_labels = []
    node_data = {}
    custom_scale = {}
    scale_index = -1

    try:
        if _nd_path:
            with open(_nd_path) as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                data_labels = reader.next()
                if 'scale' in data_labels:
                    scale_index = data_labels.index('scale')

                for row in reader:
                    if scale_index > 0:
                        custom_scale[row[0]] = min(max(float(row[scale_index]), 0.0), 1.0)
                    else:
                        custom_scale[row[0]] = 1.0
                    node_data[row[0]] = row[1:]
    except Exception,e:
        pass

    with open(_path) as f:
        reader = csv.reader(f, delimiter=';')
        if len(reader.next()) == 3:
            edges_type = edges_type[:3]
    edges = np.loadtxt( open(_path, 'rb'), delimiter=';',  skiprows = 1, dtype = edges_type )
    if len(edges_type) == 3:
        #fill the timestamp column with null timestamps if it is not in data
        timestamps = len(edges["layer"]) * ['00-00-0000']
    else:
        timestamps = edges["timestamp"]
    layer_names = sorted([ "%s" % ( layer, ) for layer in set( edges["layer"] ) ])

    unique_keys = sorted( list( set(  timestamps ) ) ) 

    print(layer_names)

    if len(unique_keys) < 100:
        nrbins = len(unique_keys)
    else:
        #shrink keyspace here by order of 10 so that we have less timestamps to deal with.
        nrbins = int( math.floor( len(unique_keys)/10 ) )

    bins = np.linspace(1, len(unique_keys), nrbins)

    keys_indices = dict( zip( unique_keys,  [ i for i in range(1,len(unique_keys) + 1 ) ] ) )
    timestamp_indices =  [ keys_indices[_ts] for _ts in timestamps ]

    #detect which timestamps to be replaced according to the binned indices array
    new_indices = np.digitize( timestamp_indices,bins )
    indices_keys = dict(  zip( new_indices, timestamps ) )
    keys_indices = dict(  zip( timestamps, new_indices ) )

    keys_replace = {}

    for _ind, _ts in enumerate( timestamps ):
        try:
            _key = keys_indices[_ts] 
            _replace_ts = indices_keys[_key] 
            keys_replace[_ind] = _replace_ts
        except Exception,e:
            print e

    for _ind,_replace_ts in keys_replace.iteritems():
        timestamps[_ind] = _replace_ts

    #now we have 10% of the initial keys ..
    unique_keys = sorted( list( set(  timestamps ) ) )

    for layer in layer_names:
        _layer_data = {}

        edges_tmp = edges[edges["layer"] == layer]

        if len(edges_type) == 3:
            timestamps_tmp = len(edges_tmp["layer"]) * ['00-00-0000']
        else:
            timestamps_tmp = edges_tmp["timestamp"]

        _edges = np.column_stack( ( edges_tmp["from"], edges_tmp["to"], timestamps_tmp ) ).tolist()
        _in_degrees = dict( matplotlib.mlab.rec_groupby(edges_tmp, ('to',), (('from', unique_ct ,'indeg'),)) )
        _nodes = np.append( edges_tmp["from"], edges_tmp["to"]  ).tolist() 
        _out_degrees = {n: len(list(group)) for n, group in groupby(sorted(edges_tmp["from"]))}

        #only possible with namedtuple:
        #_layer_data.edges = _edges
        #_layer_data.nodes = _nodes
        #_layer_data.edge_ct = len(_edges)
        #_layer_data.node_ct = len(_nodes)
        #_layer_data.in_degrees = _in_degrees

        _layer_data['edges'] = _edges
        _layer_data['nodes'] = _nodes
        _layer_data['edge_ct'] = len(_edges)
        _layer_data['node_ct'] = len(_nodes)
        _layer_data['in_degrees'] = _in_degrees
        _layer_data['out_degrees'] = _out_degrees

        max_node_ct = max(max_node_ct, len(_nodes))
        data[layer] = _layer_data

    #write edges to file
    fid = generate_id()
    tmp_name = "/tmp/edges%s" % (fid,)
    _edges = np.column_stack( ( edges["from"], edges["to"] ) )
    np.savetxt( tmp_name, _edges, fmt="%s", delimiter=' ' )


    #calculate node coords
    print "VIZUALISATION TIMER: igraph layouting :",datetime.now() 
    #read from tmp file
    ly_start = datetime.now()
    graph = MultiGraph()
    graph.igraph = igraph.Graph.Read( tmp_name , directed=directed_graph,format="ncol",weights=False )
    graph.layer_names = layer_names
    graph.data = data
    graph.custom_scale = custom_scale
    graph.max_node_ct = max_node_ct
    graph.unique_keys = unique_keys
    graph.node_data = node_data
    graph.data_labels = data_labels
    return graph



