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

/*
var onMouseDown = null;
var destroyFunction = null;
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

    function updateLayerDistance(dist) {
        var highlighted_node = graphData.highlighted_node;
        clearHighlightedObjects(renderData, graphData);

        var base_pos = 0;

        // Update y coordinate for meshes and layer_node mapping.
        // Note: this does not move any vertices, but is needed later for raycasting
        // when highlighting vertices
        $.each(graphData.node_meshes, function(i, layer_node_meshes){
            var new_pos = (base_pos + (i * dist));

            $.each(layer_node_meshes, function(j, mesh){
                mesh.position.y = new_pos;
                mesh.verticesNeedUpdate = true;
                mesh.updateMatrix();
                mesh.updateMatrixWorld();
            });

            var nodes = graphData.layer_nodes[i];
            for (var key in nodes) {
                nodes[key].coords.y = new_pos;
            }
        });

        // Move vertices (merged geometries) of each layer
        $.each(graphData.vertices_mesh, function(i, layerMesh) {
            layerMesh.position.y = (base_pos + (i * dist)) -  layerMesh.geometry.vertices[0].y;
            layerMesh.verticesNeedUpdate = true;
            layerMesh.updateMatrix();
            layerMesh.updateMatrixWorld();
        });

        function updatePosition(bg, new_y) {
             for (var j=0; j < bg.attributes.position.array.length; j++) {
                if( j % 3 == 1 ){
                    bg.attributes.position.array[j] = new_y;
                }
            }
            bg.attributes.position.needsUpdate = true;
        }

        // Move edges of each layer
        for (var i=0; i < graphData.edge_coordinates.length; i++) {  
            updatePosition(graphData.layer_lines[i].geometry, base_pos + (i * dist));
            updatePosition(graphData.layer_cones[i].geometry, base_pos + (i * dist));
        }
        if (highlighted_node != null) {
            highlightNode(graphData, renderData, highlighted_node);
        }
        renderData.render();
    }

    $( "#distanceSlider" ).slider({ 
            min: 0,
            max: graphData.y_step * 2,
            step: 50, 
            value: graphData.y_step,
            range: false,
            slide: function( event, ui ) {
                var i = ui.value; 
                updateLayerDistance( i );
            }
    });

    $( "#year" ).val( data.unique_keys[0] + " - " + data.unique_keys[data.unique_keys.length - 1]);

    for (var i = 0; i < data.layer_ct; i++) {
        $("#info-container .layer-selection ul.dropdown-menu-layers")
            .append('<li role="presentation">'+
                    '   <a role="menuitem" tabindex="-1" href="#" onclick="displayLayerInfo('+i+'); return 0;">'+data.layers[i].name+'</a></li>');
    }


    var scales = ['In Degree', 'Out Degree', 'Total Degree']; 
    if (data.custom_scale) {
        scales.push('User Defined');
    }


    $.each( scales , function( i, val ) { 
        var el = '<li role="presentation"><a role="menuitem" tabindex="-1" href="#" onclick="scaleNodes(';
        el += "'" + val + "'";
        el += '); return 0;">';
        el += val + '</a></li>';
        $("ul.dropdown-menu-scale").append(el);
    });

    var replayModes = ['single','window']
    $.each( replayModes , function( i, val ) { 
        if(val == "window"){
            var modeName = "Sliding Window"
        }else{
            var modeName = "Fixed Start"
        }

        var el = '<li role="presentation"><a role="menuitem" tabindex="-1" href="#" onclick="setReplayMode(';
        el += "'" + val + "'";
        el += '); return 0;">';
        el += modeName + '</a></li>';
        $("ul.dropdown-menu-replaymode").append(el);
    });

    var replaySpeeds = [1,2,4]
    $.each( replaySpeeds , function( i, val ) {
        var speedName = val + "x";

        var el = '<li role="presentation"><a role="menuitem" tabindex="-1" href="#" onclick="setReplaySpeed(';
        el += val;
        el += '); return 0;">';
        el += speedName + '</a></li>';
        $("ul.dropdown-menu-replayspeed").append(el);
    });

    var oldLayer = 0;
    var layerCameraPos = {0: 0};
    for (var i = 1;  i < data.layers.length ; i++) {
        if (i==1) {
            layerCameraPos[i] = layerCameraPos[i-1] + 400 +  data.width;
        } else {
            layerCameraPos[i] = layerCameraPos[i-1] + data.width;
        }
    }

    displayLayerInfo = function(id) {
        graphData.layer_index = id;
        $("#info-container .layer-selection button.dropdown-toggle").text(data.layers[id].name);
        //console.log($("#info-container .layer-selection button.dropdown-toggle"));
        $("#nrnodes").val(graphData.layer_info[id].node_count);
        $("#nredges").val(graphData.layer_info[id].edge_count);

        $("#nrcolor").val(graphData.layer_line_materials[id].color.getHexString());
        $("#nrcolor").css('background-color', '#'+graphData.layer_line_materials[id].color.getHexString());

        if (!renderData.D3) {
            renderData.controls.panLeft(renderData.camera.position.x - layerCameraPos[id]);
            renderData.controls.panUp(0 - renderData.camera.position.y);
        }
    }
    displayLayerInfo(0);


    displayShareUrl = function(){
        $("#url-container textarea").html( document.domain + data.url );   //
    }
    displayShareUrl();

    displayLayoutInfo = function(){
        if(data.layout){
            $("#layout").val( data.layout );   
        }
        else{
            $("#layout").val( "Fruchterman-Reingold" );   
        }
    }
    displayLayoutInfo();



    $("#info-container").slideDown();

    if (data.unique_keys.length > 1) {
        $("#slider-container").show();
    }

    if (data.directed) {
        $('#degreeOptions').show();
    }

    $('#nrcolor').colorpicker({ horizontal: true });
    $('#nrcolor').colorpicker().on('changeColor.colorpicker', function(event) {
        var hexStr = event.color.toHex();
        $("#nrcolor").css('background-color', hexStr);
        var color = parseInt(hexStr.slice(1, hexStr.length), 16);
        graphData.layer_lines[graphData.layer_index].material.color.setHex(color);

        if (graphData.directed) {
            graphData.layer_cones[graphData.layer_index].material.color.setHex(color);
        }
        renderData.render();
    });


    //replay tools
    function foo(start, end, round) {
        var highlighted_node = graphData.highlighted_node;
        clearHighlightedObjects(renderData, graphData);
        $("#slider").slider("option", "values", [start, end]);
        updateSlider(start, end);
        displayEdges(start, end, graphData, renderData.scene);
        if (highlighted_node != null) {
            highlightNode(graphData, renderData, highlighted_node);
        }
        renderData.render();
    }


    function loopThrough(i, min, span) {
        if ($("#replay-mode").val() === "single") {
            foo(min, i, i-min );
        } else {
            foo(i-1, i-1+span, i-min );
            if ((i-1+span) >= data.unique_keys.length-1) {
                return
            }
        }
    }

    setReplayMode = function(mode){
        $("#replay-mode").val(mode);
        if(mode=="window"){
            $("#ReplayModeMenu").text("Sliding Window");
        }else{
            $("#ReplayModeMenu").text("Fixed Start");
        }
    }

    setReplaySpeed = function(speed){
        $("#replay-speed").val(speed);
        var txt = speed + "x";
        $("#ReplaySpeedMenu").text(txt);
    }

    $('#graph-replay').click(function(e) {

        $('.graph-replay-buttons').hide()
        $('#graph-replay-pause').show();
        clearInterval( playLoop );
        
        var values = $("#slider").slider( "option", "values" );
        var min = values[0];
        var max = values[1];
        var span = max - min;
        
        if ($("#replay-mode").val() === "single") {
            span = 1;
            //max += 1;
            //always go till the end unless paused
            max = data.unique_keys.length;
        } else {
            max = data.unique_keys.length;
        }

        var mult = parseInt($("#replay-speed").val());
        
        var i=min+1;
        var round = i-min;
        

        displayEdges(min, values[1], graphData, renderData.scene);
        
        playLoop = setInterval( function() { 
                            
            var values = $("#slider").slider( "option", "values" );
            var current_max = values[1];
            if( current_max >= data.unique_keys.length - 1 ){
                $('.graph-replay-buttons').hide()
                $('#graph-replay').show();
                clearInterval( playLoop );
            }
            
            loopThrough(i,min,span) 
            i++;    
        } , round*(400/mult) )

    });

    $('#graph-replay-pause').click(function(e) {
        clearInterval( playLoop );

        var values = $("#slider").slider( "option", "values" );
        console.log("paused:", values);

        $('.graph-replay-buttons').hide();
        $('#graph-replay-continue').show();
    });
    
    $('#graph-replay-continue').click(function(e) {
        clearInterval( playLoop );

        $('.graph-replay-buttons').hide()
        $('#graph-replay-pause').show();

        var values = $("#slider").slider( "option", "values" );
        var min = values[0];
        var max = values[1];        
        var span = max - min;

        if ($("#replay-mode").val() === "single") {
            span = 1;
            //because we are contining
            min = max - 1;
            
            max = data.unique_keys.length;
            
        } else {
            max = data.unique_keys.length;
        }

        var mult = parseInt($("#replay-speed").val());
        
        var i=min+1;
        var round = i-min;
        
        //because we are contining, we do not need this
        //displayEdges(min, min, graphData, renderData.scene);
        
        playLoop = setInterval( function() { 
            
            var values = $("#slider").slider( "option", "values" );
            var current_max = values[1];
            if( current_max >= data.unique_keys.length - 1 ){
                $('.graph-replay-buttons').hide()
                $('#graph-replay').show();
                clearInterval( playLoop );
            }
            
            loopThrough(i,min,span) 
            i++;    
        } , round*(400/mult) )
    });


        renderData.hot = null;
        $("#hide-table").click(function() {
            renderData.hot.destroy();
            renderData.hot = null;
            $("#data-table").hide();
            //$("#container canvas").css("width", $(window).width());
            renderData.updateAspect();
            $("#hide-table").hide();
            $("#show-table").show();
        });

        $("#show-table").click(function() {
            //$("#container canvas").css("width", $(window).width()-450);
            $("#container").css("float", "left");
            $("#data-table").show();
            $("#data-table").css("height", $(window).height()-100);

            $("#show-table").hide();
            $("#hide-table").show();
            var container = document.getElementById('data-table');
            var percentRenderer = function (instance, td, row, col, prop, value, cellProperties) {
                Handsontable.renderers.NumericRenderer.apply(this, arguments);
                td.style.color = (value < 0) ? 'red' : 'green';
            };

            renderData.hot = new Handsontable(container, {
                data: graphData.node_data_list,
                manualColumnResize: true,
                width: 400,
                colHeaders: ["Node"].concat(graphData.data_labels.slice(1)),
                rowHeaders: false,
                stretchH: 'all',
                columnSorting: true,
                contextMenu: false,
                className: "htCenter htMiddle",
                readOnly: true,
                multiSelect: true
            }); 
            Handsontable.hooks.add('afterSelection',function(r1, c1, r2, c2) {
                if (renderData.hot.disable_event) { return ; }
                $("#clear-selection-tr").show();
                window.setTimeout(function() {
                    clearHighlightedObjects(renderData, graphData);
                    for (var j=r1; j <= r2; j++) {
                        var row = renderData.hot.getDataAtRow(j);
                        for (var i=0; i < graphData.layer_nodes.length; i++) {
                            if (row[0] in graphData.layer_nodes[i]) {
                                highlightNode(graphData, renderData, graphData.layer_nodes[i][row[0]].mesh);
                                break;
                            }
                        }
                    }
                    renderData.render();
                }, 100);
            }, renderData.hot);

        });

    renderData.render();
}
