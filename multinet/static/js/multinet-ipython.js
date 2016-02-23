/*
* Copyright (c) 2015, ETH Zurich, Chair of Systems Design
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

var destroyFunction = null;
/*
var onMouseDown = null;
var displayLayerInfo = null;

var _renderData = null;
var _graphData = null;

var playLoop;

var maxLayerDist = 1000;
var minLayerDist = 150;
var centerY = -1000;
*/

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

    if (destroyFunction != null) {
        destroyFunction();
    }

    if (destroyFunction == null && data.custom_scale) {
        $('.scale-selection button').text('User Defined')
    }

    var graphData = new GraphData();

    // store globally
    _graphData = graphData;

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

    $('#table-button').show();

    $("#clear-selection").click(function() {
        clearHighlightedObjects(renderData, graphData);
        $( "#selected_node" ).val("");
        renderData.render();
    });

    if (doAnimate) {
        animate(renderData.controls);
    }

    destroyFunction = function() {
        $('#table-button').hide();
        $('#slider-container').hide();
        $('#degreeOptions').hide();

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
        $("#info-container ul.dropdown-menu").children().remove();

        clearHighlightedObjects(renderData, graphData);

        renderData.render();
    };


    graphData.neighborhood = [];

    onMouseDown = window.addEventListener( 'mousedown', makeOnMouseDownHandler(renderData, graphData), false );

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

    /*
     * The slider
     * Timestamps/years are used to generate unique keys for the containers array. 
     * At the moment, each key is year - min_year, so that the containers keys start from 0, which makes it simple for array indexing.
     * Once the slider is moved, the corresponding containers for the omitted timestamps are set to invisible
     */

    graphData.selected_timestamps = {};
    $.each(data.unique_keys, function(i, obj) {
        graphData.selected_timestamps[obj] = true;
    });

    function updateSlider(i, j) {
        $("#year").val( data.unique_keys[i].toString() + " - " + data.unique_keys[j].toString() );
        var selected_ts = data.unique_keys.slice( i, j )                    
        displayEdges(i, j, graphData, renderData.scene);
        graphData.selected_timestamps = {};
        $.each(selected_ts, function(i, obj) {
            graphData.selected_timestamps[obj] = true;
        });
        renderData.render();
    }

    /*
    $( "#slider" ).slider({ 
            min: 0,
            max: data.unique_keys.length - 1,
            step: 1, 
            values: [ 0, data.unique_keys.length - 1 ],
            range: true,
            slide: function( event, ui ) {
                var i = ui.values[ 0 ]; 
                var j = ui.values[ 1 ];
                updateSlider(i, j);
            }
    });
    */

    renderData.render();
}
