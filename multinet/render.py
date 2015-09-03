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


SUPPORTED_LAYOUTS = ['Fruchterman-Reingold','Kamada-Kawai', 'LGL', 'Random', 'Star']
CACHE_PATH_TEMPLATE = '/tmp/multinet_{}.cpickle'


def generate_id(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def get_hash(path):
    hasher = hashlib.md5()

    with open(path) as f:
        hasher.update(f.read())
        return hasher.hexdigest()


def get_cache_path(path):
    return CACHE_PATH_TEMPLATE.format(get_hash(path))


def get_from_cache(path):
    try:
        with open(get_cache_path(path), 'rb') as f:
            return cPickle.load(f)
    except:
        return None


def cache_data(path, data):
    with open(get_cache_path(path), 'wb') as f:
        cPickle.dump(data, f, protocol=2)


def graph_layout(filename, node_data_filename, ly_alg = "fruchterman-reingold", directed_graph=True):

    cached_data = get_from_cache(filename)

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
    date_format = "%Y-%m-%d"

    #dictionary to hold all data for each layer:
    data = collections.OrderedDict()

    #data type declaration for edges to be stored in numpy array
    edges_type = [ ('from', np.str_,64), ('to', np.str_,64), ('layer', np.str_,64 ), ('timestamp', np.str_,10 ) ] 

    data_labels = []
    node_data = {}

    try:
        if _nd_path:
            with open(_nd_path) as csvfile:
                reader = csv.reader(csvfile, delimiter=';')
                data_labels = reader.next()

                for row in reader:
                    node_data[row[0]] = row[1:]

        edges = np.loadtxt( open(_path, 'rb'), delimiter=';',  skiprows = 1, dtype = edges_type )
        layers_str = [ "l%s" % ( layer, ) for layer in set( edges["layer"] ) ] 
        layers = sorted([ "%s" % ( layer, ) for layer in set( edges["layer"] ) ])

        unique_keys = sorted( list( set(  edges["timestamp"] ) ) ) 

        if len(unique_keys) < 100:
            nrbins = len(unique_keys)
        else:
            #shrink keyspace here by order of 10 so that we have less timestamps to deal with.
            nrbins = int( math.floor( len(unique_keys)/10 ) )

        bins = np.linspace(1, len(unique_keys), nrbins)

        keys_indices = dict( zip( unique_keys,  [ i for i in range(1,len(unique_keys) + 1 ) ] ) )
        timestamp_indices =  [ keys_indices[_ts] for _ts in edges['timestamp'] ]

        #detect which timestamps to be replaced according to the binned indices array
        new_indices = np.digitize( timestamp_indices,bins )
        indices_keys = dict(  zip( new_indices, edges['timestamp'] ) )
        keys_indices = dict(  zip( edges['timestamp'], new_indices ) )

        keys_replace = {}

        for _ind, _ts in enumerate( edges["timestamp"] ):
            try:
                _key = keys_indices[_ts] 
                _replace_ts = indices_keys[_key] 
                keys_replace[_ind] = _replace_ts
            except Exception,e:
                print e

        for _ind,_replace_ts in keys_replace.iteritems():
            edges["timestamp"][_ind] = _replace_ts

        #now we have 10% of the initial keys ..
        unique_keys = sorted( list( set(  edges["timestamp"] ) ) )

        for layer in layers:
            _layer_str = "l%s" % (layer,)

            #disable usage of namedtuple now in favor of pickling..
            #_layer_data = collections.namedtuple(_layer_str, ['edges', 'nodes','edge_ct','node_ct','in_degrees','coords'], verbose=False)
            _layer_data = {}

            edges_tmp = edges[edges["layer"] == layer]
            _edges = np.column_stack( ( edges_tmp["from"], edges_tmp["to"], edges_tmp["timestamp"] ) ).tolist()
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
        print "graph init failed", _path, e
        return { "graph_ready": False,  "errors": "Improper file format. Please make sure your csv file complies with the tool's format" }

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
        graph = igraph.Graph.Read( tmp_name , directed=True,format="ncol",weights=False )

        #new layouting by rcattano
        dimension = 2
        max_it = 500
        temp = 1
        nodes = len(graph.vs)
        edges = np.array( [edge.tuple for edge in graph.es], np.int32)

        pos = math.sqrt(nodes) * np.random.random_sample( (nodes, dimension) ) - math.sqrt(nodes)/2
        #float6Pos = np.copy( pos.astype(np.float32) )
        pos = pos.astype(np.float32)
        fl.layout_fr_omp_simd( edges, pos , max_it, temp )

        #get the Layout object here. 
        #http://igraph.org/python/doc/igraph.layout.Layout-class.html
        widthCoeff = 1
        scl =  int( _l/ 100 ) #int( _l * _l / 10 )
        if ly_alg == "Fruchterman-Reingold":
            ly = igraph.Layout( tuple(map(tuple, pos )) )
            scl = scl / 3
        elif ly_alg == "LGL":
            ly = graph.layout_lgl()
        elif ly_alg == "Kamada-Kawai":
            ly = graph.layout_kamada_kawai()
            scl = scl / 10
        elif ly_alg == "Star":
            ly = graph.layout_star()
            scl =  scl * 2
            widthCoeff = 100
        elif ly_alg == "Random":
            ly = graph.layout_random()
            scl =  scl * 2
            widthCoeff = 100
        else:
            ly = igraph.Layout( tuple(map(tuple, pos )) )
            scl = scl / 3
            #ly_alg = "Fruchterman-Reingold"
            #OR standard fruchterman reingold
            #ly = graph.layout_fruchterman_reingold(dim=2,coolexp =1, area = int( _l * _l / 10 ) )

        ly_end = datetime.now()
        diff = ly_end - ly_start

        print "VIZUALISATION TIMER: returning coordinates :",ly_end
        print "Layouting took :", diff.seconds, "seconds using", ly_alg 

        boundaries = ly.boundaries()
        ly_width = abs(boundaries[0][0]) + abs(boundaries[1][0])    
        ly_width = ly_width * widthCoeff

        ly.scale( scl )

        print "width:", ly_width, scl
        print(ly.boundaries())

        boundaries = ly.boundaries()
        width2 = abs(boundaries[0][0]) + abs(boundaries[1][0])

        coords = ly.__dict__['_coords']
        print type( coords[0][0] ), type( coords[0][1] )
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
                coords[node_id] = [ all_coords[ node_id ], _common, indeg, outdeg, indeg + outdeg ] 

                max_out_deg = max(max_out_deg, outdeg)
                max_in_deg = max(max_in_deg, indeg)
                max_total_deg = max(max_total_deg, outdeg + indeg)
            #possible with namedtuples
            #_layer_data.coords = coords

            _layer_data['coords'] = coords

            # add dummy 0 values, so max_in_degree and max_out_degree have to 
            # same offset as the node's degrees
            _layer_data['maxDeg'] = [0, 0, max_in_deg, max_out_deg, max_total_deg] 

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

        data['layer_ct'] = len(data)
        data['max_node_ct'] = max_node_ct
        data['unique_keys'] = unique_keys
        data['width'] = ly_width   
        data['width2'] = width2
        data['layout'] = ly_alg
        data['layers'] = [data[l] for l in sorted(layers)]
        data['node_data'] = node_data
        data['data_labels']= data_labels

        data = dict(data)

        cache_data(filename, data)

        return data

    except Exception,e:
        print "graph rendering failed", e
        return { "graph_ready": False,  "errors": e, }
