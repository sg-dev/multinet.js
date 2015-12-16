/*
* Copyright (c) 2015, ETH Zurich, Chair of Systems Des_ign
* All rights reserved.
*
* Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
*
* 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
*
* 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
*
* 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
*
* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/



var maxLayerDist = 1000;
var minLayerDist = 150;


if ( ! Detector.webgl ) Detector.addGetWebGLMessage();

function RenderData() {
    // renderer
    this.renderer = new THREE.WebGLRenderer( {
        antialias: true,
        preserveDrawingBuffer: true,   // required to support .toDataURL()
    });

    //renderer.setClearColor( scene.fog.color );
    this.renderer.setPixelRatio( window.devicePixelRatio );
    this.renderer.setSize( $('#container').width(), $('#container').height());
    this.renderer.setClearColor( 0xffffff );
    this.renderer.sortObjects = false;

    this.controls = null;

    this.controlEventListener = null;

    var that = this;

    function updateCameraPosition(currentPosition, that) {
        if (currentPosition) {
            that.camera.position.x = currentPosition.x; 
            that.camera.position.y = currentPosition.y; 
            that.camera.position.z = currentPosition.z;
        }

        if (that.controls == null) {
            that.controls = new THREE.OrbitControls( that.camera, document.getElementById("container") );
            that.controls.addEventListener( 'change', function() { that.render(); } );
        } else {
            that.controls.object = that.camera;
        }
        that.controls.zoom = 1;
    }

    //perspective camera
    this.usePerspectiveCamera = function(currentPosition) {
        that.camera = new THREE.PerspectiveCamera(
                40, $('#container').width() / $('#container').height(), 1, 100000
        );

        updateCameraPosition(currentPosition, that);
    };

    this.useOrthographicCamera = function(currentPosition) {
        that.camera = new THREE.OrthographicCamera(
                2 * $('#container').width() / - 1,
                2 *  $('#container').width() / 1,
                2 *  $('#container').height() / 1,
                2 *  $('#container').height() / - 1,
                -5000, 100000
        );

        updateCameraPosition(currentPosition, that);
    };

    this.usePerspectiveCamera();

    this.updateAspect = function() {
        var canvas = $("#container canvas");
        that.camera.aspect = $('#container').width() / $('#container').height();
        that.camera.updateProjectionMatrix();
        that.renderer.setSize( $('#container').width(), $('#container').height());
        that.render();
    };


    this.container = document.getElementById( 'container' );
    this.container.appendChild( this.renderer.domElement );

    /*
    this.stats = new Stats();
    this.stats.domElement.style.position = 'absolute';
    this.stats.domElement.style.bottom= '0px';
    this.stats.domElement.style.zIndex = 100;
    this.container.appendChild( this.stats.domElement );
    */

    this.scene = new THREE.Scene();

    //this.vertex_geometry = new THREE.BoxGeometry( 20, 20, 20);

    window.addEventListener('resize', function onWindowResize() {
        that.updateAspect();
    }, false);

    this.render = function render() {
        that.renderer.render(that.scene, that.camera);
        //that.stats.update();
    };
}


function RenderDataSVG(currentPosition) {
    // renderer
    this.renderer = new THREE.SVGRenderer( { antialias: true } );
    //renderer.setClearColor( scene.fog.color );
    this.renderer.setPixelRatio( window.devicePixelRatio );
    this.renderer.setSize( $('#container').width(), $('#container').height());
    this.renderer.setClearColor( 0xffffff );
    this.renderer.sortObjects = false;

    this.camera = new THREE.PerspectiveCamera( 40, $('#container').width() / $('#container').height(), 1, 100000 );

    if(currentPosition){
        this.camera.position.x = currentPosition.x; 
        this.camera.position.y = currentPosition.y; 
        this.camera.position.z = currentPosition.z;
    }


    var that = this;

    this.container = document.getElementById( 'container' );
    this.container.appendChild( this.renderer.domElement );

    window.addEventListener('resize', function onWindowResize() {
        that.camera.aspect = $('#container').width() / $('container').height;
        that.camera.updateProjectionMatrix();

        that.renderer.setSize( $('#container').width(), $('#container').height());

        that.render();
    }, false);

    this.scene = new THREE.Scene();

    //this.vertex_geometry = new THREE.BoxGeometry( 20, 20, 20);

    this.render = function render() {
        that.renderer.render(that.scene, that.camera);
    };
}


function GraphData() {
    this.node_meshes = [];
    this.layer_nodes = [];
    this.edge_coordinates = [];

    this.layer_cones = [];
    this.layer_timestamp_offsets = [];
    this.layer_line_materials = [
        new THREE.LineBasicMaterial( { color: 0xA00000, opacity: 0.2, transparent: true, linewidth: 1 } ),
        new THREE.LineBasicMaterial( { color: 0x0A0000, opacity: 0.2, transparent: true, linewidth: 1 } ),
        new THREE.LineBasicMaterial( { color: 0x00A000, opacity: 0.2, transparent: true, linewidth: 1 } )
    ];

    this.vertexMaterial = new THREE.MeshFaceMaterial([
        new THREE.MeshBasicMaterial({color:0x000000, fog: false}),
        new THREE.MeshBasicMaterial({color:0x0000ff, fog: false}),
    ]);

    this.coneMaterial = [
        new THREE.MeshBasicMaterial({color:0xA00000, opacity: 0.4, transparent: true, fog: false}),
        new THREE.MeshBasicMaterial({color:0x0A0000, opacity: 0.4, transparent: true, fog: false}),
        new THREE.MeshBasicMaterial({color:0x00A000, opacity: 0.4, transparent: true, fog: false}),
    ];


    this.layer_index = 0;

    this.neighborhood_material = new THREE.LineBasicMaterial( { color: 0x006400, transparent: true, linewidth: 3 } );

    this.layer_lines = [];

    this.vertices_mesh = [];
    this.vertices_geom = []; //new THREE.Geometry();

    this.highlight_material = new THREE.MeshBasicMaterial({color:0x006400, fog: false});
    this.highlight_meshes = [];
    this.highlight_geometries = [];

    this.neighborhood = null;
    this.neighborhood_lines = [];

    this.layer_info = {};

    this.selected_timestamps = {};
}

function animate(controls) {
    requestAnimationFrame(function() { animate(controls); });
    controls.update();
}

function addArrows(edges, a_positions, a_indices) {
    for (var j=1; j < edges.length; j += 2 ) {
        var A = new THREE.Vector3(edges[j-1].x, edges[j-1].y, edges[j-1].z);
        var B = new THREE.Vector3(edges[j].x, edges[j].y, edges[j].z);
        if (A.equals(B)) {
            continue;
        }

        var dir = B.clone().sub(A).normalize();
        var length = 100;
        var hex = 0xffff00;

        var coneGeometry = new THREE.CylinderGeometry( 0, 0.5, 1, 5, 1 );
        coneGeometry.applyMatrix( new THREE.Matrix4().makeTranslation( 0, - 0.5, 0 ) );
        var cone = new THREE.Mesh( coneGeometry, new THREE.MeshBasicMaterial( { color: hex } ) );

        cone.matrixAutoUpdate = false;

        cone.scale.set( 5, 10, 1);
        var distance = A.distanceTo(B);
        if (distance < 2) {
            if (B.distanceTo(A) < 2) {
            }
        }
        cone.position.copy(A.add(dir.clone().multiplyScalar(A.distanceTo(B)-2)));

        var axis = new THREE.Vector3();
        var radians;
        if ( dir.y > 0.99999 ) {
            cone.quaternion.set( 0, 0, 0, 1 );
        } else if ( dir.y < - 0.99999 ) {
            cone.quaternion.set( 1, 0, 0, 0 );
        } else {
            axis.set( dir.z, 0, - dir.x ).normalize();
            radians = Math.acos( dir.y );
            cone.quaternion.setFromAxisAngle( axis, radians );
        }

        cone.updateMatrix();
        cone.updateMatrixWorld(true);

        from_mesh(cone, a_positions, a_indices)
    }
}

function displayEdgesInitial(keys, graphData, scene) {
    graphData.layer_lines = [];

    graphData.layer_starts = [];

    for (var i=0; i < graphData.edge_coordinates.length; i++) {  
        var verts = [];
        var starts = [];
        var starts_arrows = []
        var a_indices = [];
        var a_positions = [];
        var indices = [];

        $.each(keys, function(foo, key) {
            starts.push({edges: verts.length, arrows: a_indices.length});
            if (graphData.edge_coordinates[i][key] !== undefined) {
               verts = verts.concat(graphData.edge_coordinates[i][key]);
               var edges = graphData.edge_coordinates[i][key];
               if (graphData.directed) {
                   addArrows(edges, a_positions, a_indices);
                }
            }
        });

        starts.push({edges: verts.length, arrows: a_indices.length});
        graphData.layer_starts.push(starts);

        var positions = new Float32Array( verts.length * 3 );

        var vs = [];

        for (var j=0; j < verts.length; j++) {
            indices.push(j);
            positions[j*3] = verts[j].x;
            positions[j*3+1] = verts[j].y;
            positions[j*3+2] = verts[j].z;

        }

        var geometry = new THREE.BufferGeometry();
        geometry.addAttribute( 'index', new THREE.BufferAttribute( new Uint32Array(a_indices), 1 ) );
        geometry.addAttribute( 'position', new THREE.BufferAttribute( new Float32Array(a_positions), 3 ) );
        geometry.computeBoundingSphere();
        geometry.computeVertexNormals();

        bg = addGeomentry(geometry, graphData.coneMaterial[i], scene);
        bg.scale.set( 5, 10, 1);
        graphData.layer_cones.push(bg);

        var bg = new THREE.BufferGeometry();
        bg.addAttribute( 'index', new THREE.BufferAttribute( new Uint32Array(indices), 1 ) );
        bg.addAttribute( 'position', new THREE.BufferAttribute( positions, 3 ) );

        bg.computeBoundingSphere();
        graphData.layer_lines.push(new THREE.Line(bg, graphData.layer_line_materials[i], THREE.LinePieces));
        scene.add( graphData.layer_lines[i] );
    }
}
function from_mesh(mesh, positions, indices) {

    for ( var i = 0; i < mesh.geometry.faces.length; i += 1 ) {
        indices.push((positions.length/3)+mesh.geometry.faces[i].a);
        indices.push(positions.length/3+mesh.geometry.faces[i].b);
        indices.push(positions.length/3+mesh.geometry.faces[i].c);
    }

    for ( var i = 0; i < mesh.geometry.vertices.length; i += 1 ) {
        var v = mesh.geometry.vertices[i].clone().applyMatrix4(mesh.matrixWorld);
        var i3 = i * 3;
        positions.push(v.x);
        positions.push(v.y);
        positions.push(v.z);
    }
}

function displayEdges(start, end, graphData, scene) {
     for (var i=0; i < graphData.edge_coordinates.length; i++) {  
        var bg = graphData.layer_lines[i].geometry;
        bg.drawcalls.splice(0, 1);
        bg.addDrawCall(graphData.layer_starts[i][start].edges, graphData.layer_starts[i][end].edges-graphData.layer_starts[i][start].edges);

        var bg = graphData.layer_cones[i].geometry;

        bg.drawcalls.splice(0, 1);
        bg.addDrawCall(graphData.layer_starts[i][start].arrows, graphData.layer_starts[i][end].arrows-graphData.layer_starts[i][start].arrows);
    }
}

/*
*  Create a node mesh object and merged it with `parent_geometry`.
*/
function addNode(node, parent_geometry, materialIndex, graphData, scale, layer_node_meshes) {
    var scl = scale; 
    if(scl <= 2) {
        scl = 1
    };

    if( scl == 3  ){ 
        //circle args = radius, #segments in circle
        var tmp_geometry = new THREE.CircleGeometry( scl, 8 );  
        //var tmp_geometry = new THREE.BoxGeometry( 20 + scl, 20 + scl, 20 + scl);
    } else {
        var tmp_geometry = new THREE.SphereGeometry( scl, 0, 0 );
    }
    var mesh = new THREE.Mesh(tmp_geometry);
    mesh.position.x = node.coords.x;
    mesh.position.y = node.coords.y;
    mesh.position.z = node.coords.z;

    mesh.updateMatrix();
    mesh.updateMatrixWorld(true);
    mesh.node_id = node.id;
    mesh.degree = node.degree;
    node.mesh = mesh;

    parent_geometry.merge(mesh.geometry, mesh.matrix, materialIndex);
    layer_node_meshes.push(mesh);
}

function addEdge(source, target, year, edge_coordinates) {
    var edge_coords = edge_coordinates[year];
    if (edge_coords === undefined) {
        edge_coordinates[year] = [];
        edge_coords = edge_coordinates[year];
    }

    edge_coords.push(source.coords);
    edge_coords.push(target.coords);
}

function transformTo2D(coords, layer_id, width) {
    var new_coords = {};
    new_coords.x = coords[0];
    new_coords.y = coords[1];
    new_coords.z = 0;

    if (layer_id > 0) {
        new_coords.x += 400 + (layer_id) * width;
    }

    return new_coords;
}

function transformTo3D(coords, layer_id, y_step) {
    var new_coords = {};

    new_coords.x = coords[0];
    new_coords.y = y_step * (layer_id);
    new_coords.z = coords[1];

    return new_coords;
}

function createLayer(data, area, layer_id, graphData, coordinateTransformer, dataWidth, degreeSelector) {
    layer_edge_coordinates = {};
    graphData.edge_coordinates.push(layer_edge_coordinates);
    graphData.neighborhood.push(data.neighborhood);

    var maxDegLayer = degreeSelector(data.maxDeg);
    var maxSize = Math.pow(dataWidth, 1/3);

    var nodes = graphData.layer_nodes[layer_id];
    var layer_node_geom = new THREE.Geometry();
    var layer_node_meshes = [];
    $.each(data.coords, function(node_id, node_data) {
        var node_coords = node_data[0];
        var node_common = node_data[1];
        var node_degree = degreeSelector(node_data);

        var source = {};
        source.id = node_id;
        source.degree = node_degree

        source.coords = coordinateTransformer(node_coords, layer_id);

        nodes[node_id] = source;

        var scale = ( node_degree / maxDegLayer ) * maxSize;

        if( node_common == 1){  
            addNode(source, layer_node_geom, 1, graphData, scale, layer_node_meshes);
        }
        else { 
            addNode(source, layer_node_geom, 0, graphData, scale, layer_node_meshes);
        }
    });
    graphData.node_meshes.push(layer_node_meshes);
    graphData.vertices_geom.push(layer_node_geom);

    $.each(data.edges, function(i, points) {
        var source = nodes[points[0]];

        var target = nodes[points[1]];
        var year = points[2];
        addEdge(source, target, year, layer_edge_coordinates);
    });

    var layer_info = {
        node_count: Object.keys(nodes).length,
        edge_count: data.edge_ct
    };
    return { nodes: nodes, info: layer_info };
}

function createGraph2D(data, renderData) {
    renderData.D3 = false;
    renderData.usePerspectiveCamera();
    renderData.controls.noRotate = true;

    // Limit panning
    renderData.controls.minYPan = -2000;
    renderData.controls.maxYPan = 2000;
    renderData.controls.minXPan = data.layer_ct * data.width * -1.5;
    renderData.controls.maxXPan = data.layer_ct * data.width * 3;

    // attempt to center the graph to camera wrt its size
    // inspired by http://stackoverflow.com/questions/13350875/three-js-width-of-view/13351534#13351534
    var vFOV = renderData.camera.fov * Math.PI / 180; 
    var ratio = 2 * Math.tan( vFOV / 2 );
    var aspect = $('#container').width() / $('#container').height();
    var d1 = data.width / ratio;
    var d2 = data.width / (ratio * aspect)
    var dist = Math.max(d1, d2);

    renderData.camera.position.z = 1.5 * dist;

    // update camera.far and controls to calculated distance
    renderData.controls.maxDistance = 2 *  dist;
    renderData.camera.far = 2.1 * dist;
    renderData.camera.updateProjectionMatrix();

     return createGraph(data, renderData, function(coords, layer_id) {
        return transformTo2D(coords, layer_id, data.width);
    }, true);
}

function createGraph3D(data, renderData, degreeSelector) {
    var y_range = data.width;
    var y_step = Math.max( Math.min(y_range / data.layer_ct / 2 , maxLayerDist ) , minLayerDist);

    y_range = (data.layer_ct-1) * y_step;

    renderData.D3 = true;
    renderData.usePerspectiveCamera();
    renderData.controls.noRotate = false;

    // Limit panning
    renderData.controls.minYPan = -2000;
    renderData.controls.maxYPan = 2000;
    renderData.controls.minXPan = data.width * -1.5;
    renderData.controls.maxXPan = data.width * 2;

    // attempt to center the graph to camera wrt its size
    // inspired by http://stackoverflow.com/questions/13350875/three-js-width-of-view/13351534#13351534
    var vFOV = renderData.camera.fov * Math.PI / 180; 
    var ratio = 2 * Math.tan( vFOV / 2 );
    var aspect = $('#container').width() / $('#container').height();
    var d1 = y_range / ratio;
    var d2 = data.width / (ratio * aspect)
    var dist = Math.max(d1, d2);

    renderData.camera.position.z = 1.5 * dist;
    renderData.camera.position.x = 0;
    renderData.camera.position.y = y_range * 0.5;
    renderData.controls.target = new THREE.Vector3(0, 0.5 * y_range, 0);

    // update camera.far and controls to calculated distance
    // Limit maximum scroll distance; it should be definitely smaller than the
    // FAR parameter of the camera
    renderData.controls.maxDistance = 2 *  dist;

    // update camera.far and controls to calculated distance
    renderData.camera.far = 2.1 * dist + data.width;
    renderData.camera.updateProjectionMatrix();

    return createGraph(data, renderData, function(coords, layer_id) {
        return transformTo3D(coords, layer_id, y_step);
    }, true, degreeSelector);
}

function createGraph3DStatic(data, renderData) {
    var y_range = data.width;
    var y_step = Math.max( Math.min(y_range / (data.layer_ct-1) / 2 , maxLayerDist ) , minLayerDist);

    y_range = data.layer_ct * y_step;

    return createGraph(data, renderData, function(coords, layer_id) {
        return transformTo3D(coords, layer_id, y_step);
    }, false);
}

function destroyGraph(renderData, graphData) {
    window.removeEventListener('mousedown', renderData.onMouseDown);

    clearHighlightedObjects(renderData, graphData);

    if (graphData.layer_lines.length == 0) {

        return;
    }

    for (var i=0; i < graphData.layer_lines.length; i++) {
        renderData.scene.remove(graphData.layer_lines[i]);
        renderData.scene.remove(graphData.layer_cones[i]);
        graphData.layer_lines[i].geometry.dispose();
        graphData.layer_cones[i].geometry.dispose();
    }
    graphData.edge_coordinates = null;

    $.each(graphData.node_meshes, function(i, layer_node_meshes) {
        $.each(layer_node_meshes, function(i, obj) {
            obj.geometry.dispose();
        });
    });

    graphData.layer_lines = [];

    graphData.edge_coordinates= {};

    $.each(graphData.vertices_mesh, function(i, obj) {
        renderData.scene.remove(obj);
    });

    graphData.vertices_mesh = null;
    for (var i=0; i < graphData.vertices_geom.length; i++) {
        renderData.scene.remove(graphData.vertices_geom[i]);
        graphData.vertices_geom[i].dispose();
    }
    graphData.vertices_geom = [];

    renderData.layer_info = {};

    clearHighlightedObjects(renderData, graphData);

    renderData.render();
}

function createGraph(data, renderData, coordinateTransformer, doAnimate, degreeSelector) {
    if (degreeSelector == undefined) {
        if (data.custom_scale) {
            var degreeSelector = function(v) {
                return v[5];
            };
        } else {
            var degreeSelector = function(v) {
                return v[2];
            };
        }
    }

    var graphData = new GraphData();

    graphData.directed = data.directed;

    graphData.layers = data.layers;
    graphData.node_data = data.node_data;
    graphData.data_labels = data.data_labels;

    graphData.node_data_list = [];
    for (var key in graphData.node_data) {
      if (graphData.node_data.hasOwnProperty(key)) {
        graphData.node_data_list.push([key].concat(graphData.node_data[key]));
      }
    }

    if (doAnimate) {
        animate(renderData.controls);
    }

    graphData.neighborhood = [];

    renderData.onMouseDown = window.addEventListener( 'mousedown', makeOnMouseDownHandler(renderData, graphData), false );

    var area = data.max_node_ct;
    var num_edges = data.edgect1 + data.edgect2;

    var y_range = data.width;
    graphData.y_range = y_range;
    var y_step = Math.max( Math.min(y_range / (data.layer_ct-1) , maxLayerDist ) , minLayerDist);
    graphData.y_step = y_step;

    var node_cnt = 0;

    for (var i = 0; i < data.layer_ct; i++) {
        graphData.layer_nodes.push({});
        // NOTE: when changing y here, make sure to change it in transfromTo3D as well
        var y = (-y_range) + (y_step*(i));
        var res = createLayer(data.layers[i], area, i, graphData, coordinateTransformer, data.width, degreeSelector);
        graphData.layer_info[i] = res.info;
    }

    displayEdgesInitial(data.unique_keys, graphData, renderData.scene);

    displayEdges(0, data.unique_keys.length, graphData, renderData.scene);

    for (var i=0; i < graphData.vertices_geom.length; i++) {
        graphData.vertices_mesh.push(addGeomentry(graphData.vertices_geom[i], graphData.vertexMaterial, renderData.scene));
    }

    renderData.render();

    return {
        graphData: graphData,
        destroyFunction: function() { destroyGraph(renderData, graphData) }
    };
}

/*
 * adds a (merged) geometry to the scene
 */
function addGeomentry(geometry, material, scene) {
    geometry.computeFaceNormals();
    group = new THREE.Mesh(geometry, material);
    group.matrixAutoUpdate = false;
    group.updateMatrix();
    scene.add( group );
    return group;
}

function clearHighlightedObjects(renderData, graphData) {
    $("#popup").hide();
    for (var i=0; i < graphData.highlight_meshes.length; i++) {
        renderData.scene.remove(graphData.highlight_meshes[i]);
        graphData.highlight_meshes[i].geometry.dispose();

        renderData.scene.remove(graphData.neighborhood_lines[i]);
        graphData.neighborhood_lines[i].geometry.dispose();
        $("#clear-selection-tr").hide();
    }
    graphData.highlight_meshes = [];
    graphData.neighborhood_lines = [];
    graphData.highlighted_node = null;
}

function highlightNeighbors(neighborhood_geometry, highlight_geom, graphData, node, node_id, layer_id) {
    var coords1 = node.position;
    var nodes = graphData.layer_nodes[layer_id];

    // highlight neighboring nodes and edges in the layer of the selected node
    $.each(graphData.layers[layer_id].neighborhood[node_id], function(i, obj) {
        if (!(obj[0] in nodes) || !(obj[1] in graphData.selected_timestamps)) {
            return;
        }
        var coords2 = nodes[obj[0]].coords;

        neighborhood_geometry.vertices.push(coords1);
        neighborhood_geometry.vertices.push(coords2);

        var mesh = nodes[obj[0]].mesh;
        highlight_geom.merge(mesh.geometry, mesh.matrix);
    });
}

function showPopup(x, y, node_id, data, labels) {
    var table = '<table class="table table-striped" style="margin-bottom: 0 !important;width:auto !important;">';
    if (labels.length == 0) {
        return; 
    } 

    table += '<tr>\n<td>ID</td>\n<td>'+ node_id +'</td></tr>';

    $.each(data, function(i, obj) {
        table += '<tr>\n<td>'+labels[i+1]+'</td>\n<td>'+obj+'</td></tr>';
    });
    $("#popup").html(table);

    var viewportWidth = $(window).width() - $("#info-container").width();
    var viewportHeight = $(window).height() - $("#slider-container").height();
    var boxHeight = $("#popup").height();
    var boxWidth = $("#popup").width();
    var boxX = x + 20;
    var boxY = y;
    if ((boxY + boxHeight) > viewportHeight) {
        boxY = viewportHeight - boxHeight - 40;
    }

    if ((boxX + boxWidth) > viewportWidth) {
        boxX = boxX - boxWidth - 40;
    }

    $("#popup").css("position", "absolute")
        .css("left", boxX)
        .css("top", boxY)
        .show();
}

function highlightNode(graphData, renderData, node) {

    var highlight_geom = new THREE.Geometry();
    var neighborhood_geometry = new THREE.Geometry();
    graphData.highlighted_node = node;

    var row = 0;
    for (; row < graphData.node_data_list.length; row++) {
        if (graphData.node_data_list[row][0] == node.node_id) {
            break;
        }
    }

    if (renderData.hot != null) {
        renderData.hot.disable_event = true;
        // this is needed because handsontable does not scroll to selection for
        // the second selectCell call
        renderData.hot.selectCell(row, 0, row, 0, true);
        renderData.hot.selectCell(row, 0, row, renderData.hot.countCols()-1, true);
        renderData.hot.disable_event = false;
    }
    // highlight the selected node in the other layers, including an edge between the layers
    for (var i=0; i < graphData.layer_nodes.length; i++) {
        if (node.node_id in graphData.layer_nodes[i]) {
            var highlighted_node = graphData.layer_nodes[i][node.node_id].mesh.clone();
            highlightNeighbors(neighborhood_geometry, highlight_geom, graphData, highlighted_node, node.node_id, i);
            highlighted_node.scale.x += 0.3;
            highlighted_node.scale.y += 0.3;
            highlighted_node.scale.z += 0.3;
            highlight_geom.merge(highlighted_node.geometry, highlighted_node.matrix);
            neighborhood_geometry.vertices.push(node.position);
            neighborhood_geometry.vertices.push(graphData.layer_nodes[i][node.node_id].coords);
        }
    }

    neighborhood_line = new THREE.Line(neighborhood_geometry, graphData.neighborhood_material, THREE.LinePieces);
    renderData.scene.add(neighborhood_line);
    graphData.neighborhood_lines.push(neighborhood_line);

    graphData.highlight_meshes.push(addGeomentry(highlight_geom, graphData.highlight_material, renderData.scene));
}


function makeOnMouseDownHandler(renderData, graphData) {
    return function onMouseDown( event ) {
        var update_scene = false;

        var mouse = new THREE.Vector2();
        mouse.x = ( (event.clientX-$('#container').offset().left) / renderData.renderer.domElement.width ) * 2 - 1;
        mouse.y = - ( ($(window).scrollTop()+event.clientY - $('#container').offset().top) / renderData.renderer.domElement.height) * 2 + 1;

        var raycaster = new THREE.Raycaster();
        raycaster.setFromCamera( mouse, renderData.camera );

        var intersects = [];
        $.each(graphData.node_meshes, function(i, layer_node_meshes) {
            intersects = intersects.concat(raycaster.intersectObjects(layer_node_meshes, raycaster));
        });

        var nearest_intersection = {
            distance: Math.pow(2,32) - 1,
        };

        console.log("found ", intersects.length, " intersections");
        $.each(intersects, function(i, obj) {
            if (nearest_intersection.distance > obj.distance) {
                nearest_intersection = obj;
            }
        });

         if (nearest_intersection.hasOwnProperty('object') && nearest_intersection.object.hasOwnProperty('node_id')) {


            if (!event.ctrlKey) {
                clearHighlightedObjects(renderData, graphData);
            }
            $("#clear-selection-tr").show();
            var selected_node = nearest_intersection.object;

            showPopup(event.clientX, event.clientY, selected_node.node_id, graphData.node_data[selected_node.node_id], graphData.data_labels);

            update_scene = true;

            $( "#selected_node" ).val(selected_node.node_id);

            highlightNode(graphData, renderData, selected_node);
        }

        if (update_scene) {
            renderData.render();
        }
    }
}
