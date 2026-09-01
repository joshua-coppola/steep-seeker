function run_map(trails, map, editable = false){
    // Delete-mode state (management edit page only, when editable is true):
    // a set of flagged trail/lift OSM ids and a toggle for whether a click
    // flags a line for deletion instead of opening its popup.
    let deleteMode = false;
    const flagged = new Set();
    // Orange dash-dot ( -- - -- - ) -- deliberately unlike the red
    // difficulty lines and the gladed lines' even dashes (dashArray '5,10').
    const FLAGGED_STYLE = {
        color: '#ff7f0e',
        weight: 7,
        opacity: 0.95,
        dashArray: '20,10,10,10',
        lineCap: 'round',
    };

    function updateBulkDeleteForm() {
        const count = document.getElementById('bulk-delete-count');
        if (count) count.textContent = flagged.size + ' flagged';
        const submit = document.getElementById('bulk-delete-submit');
        if (submit) submit.disabled = flagged.size === 0;
    }

    // A direct click on a line fires both the layer's own "click" and
    // Leaflet.AlmostOver's "almost:click"; this collapses that pair (and
    // any accidental double-click) into a single flag toggle per id.
    let lastToggle = {id: null, at: 0};

    function toggleFlag(layer) {
        const id = layer.feature && layer.feature.properties.item_id;
        if (!id) return;
        const now = Date.now();
        if (lastToggle.id === id && now - lastToggle.at < 400) return;
        lastToggle = {id: id, at: now};
        if (flagged.has(id)) {
            flagged.delete(id);
            geojson_features.resetStyle(layer);
        } else {
            flagged.add(id);
            layer.setStyle(FLAGGED_STYLE);
        }
        updateBulkDeleteForm();
    }

    function isFlagged(layer) {
        return layer.feature && flagged.has(layer.feature.properties.item_id);
    }

    // Define two basemaps
    const topoBasemap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Data: OSM, USGS. Tiles &copy; Esri'
    });
    
    const satelliteBasemap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Data: OSM, USGS. Tiles &copy; Esri'
    });
    
    // Add the default basemap
    topoBasemap.addTo(map);
    
    // Track current basemap
    let currentBasemap = 'topo';
    
    // Create basemap toggle control
    L.Control.BasemapToggle = L.Control.extend({
        onAdd: function(map) {
            const button = L.DomUtil.create('button');
            button.innerHTML = 'Satellite';
            button.className = 'basemap-toggle-btn';
            
            button.onclick = function() {
                if (currentBasemap === 'topo') {
                    map.removeLayer(topoBasemap);
                    map.addLayer(satelliteBasemap);
                    button.innerHTML = 'Topo';
                    currentBasemap = 'satellite';
                } else {
                    map.removeLayer(satelliteBasemap);
                    map.addLayer(topoBasemap);
                    button.innerHTML = 'Satellite';
                    currentBasemap = 'topo';
                }
                
                // Update trail labels
                updateTrailLabels();
            };
            
            return button;
        }
    });
    
    // Add the toggle control to map
    L.control.basemapToggle = function(opts) {
        return new L.Control.BasemapToggle(opts);
    }
    
    L.control.basemapToggle({ position: 'topright' }).addTo(map);

    let heightgraph_width = 800;
    let heightgraph_height = 280;
    let position = "bottomleft";

    function getWidth() {
        return Math.max(
            document.body.scrollWidth,
            document.documentElement.scrollWidth,
            document.body.offsetWidth,
            document.documentElement.offsetWidth,
            document.documentElement.clientWidth
        );
    }

    let window_width = getWidth();
    if(window_width < 1400) {
        heightgraph_width = window_width - 632;
    }
    if(window_width <=  950){
        heightgraph_width = window_width - 20;
    }
    if(window_width <= 500){
        heightgraph_width = window_width - 20;
        heightgraph_height = 200;
    }
    position = "topright";

    const hg = L.control.heightgraph({
        mappings: colorMappings,
        graphStyle: {
            opacity: 0.8,
            'fill-opacity': 0.5,
            'stroke-width': '2px'
        },
        expandControls: true,
        expand: false,
        position: position,
        width: heightgraph_width,
        height: heightgraph_height,
        highlightStyle: {
            color: "purple"
        },
        translation: {
            distance: "Distance",
            elevation: "Elevation",
            segment_length: "Segment Length",
            type: "Rating",
            legend: "Legend"
        },
        margins: {
            top: 30,
            right: 30,
            bottom: 50,
            left: 75
        }
    }).addTo(map);

    setTimeout(() => {
        const svg = document.querySelector(".heightgraph svg");
        if (!svg) return;
      
        const title = document.createElementNS("http://www.w3.org/2000/svg", "text");
        title.setAttribute("x", "50%");
        title.setAttribute("y", "20");
        title.setAttribute("text-anchor", "middle");
        title.setAttribute("class", "heightgraph-svg-title");
        title.textContent = "Elevation Profile (No Trail Selected)";
      
        svg.prepend(title);
    });

    function onEachFeature(feature, layer) {
        if (feature.properties && feature.properties.popupContent) {
            layer.bindPopup(feature.properties.popupContent);
        }
        if (feature.properties && feature.properties.label && map.getZoom() > 14) {
            const textColor = currentBasemap === 'satellite' ? 'white' : 'black';
            layer.setText(feature.properties.label, {
                offset: -5,
                center: true,
                orientation: feature.properties.orientation,
                attributes: {
                    fill: textColor,
                    'font-size': '14px'
                }
            });
        }
    }

    function style(feature) {
        if (feature.properties.isRoute) {
            return {
                color: feature.properties.color,
                weight: 16,
                opacity: 0.25,
                interactive: false,
                lineCap: 'round',
                lineJoin: 'round',
                className: 'route-line-soft'
            }
        }
        if (feature.properties.gladed) {
            if (feature.properties.gladed == 'True') {
                return {color: feature.properties.color, weight: 4, dashArray: '5,10'}
            }
        }
        return {color: feature.properties.color, weight: 4}
    }

    function point_color(point) {
        if(point < 18){
            return "green";
        };
        if(point < 27){
            return "royalblue";
        };
        if(point < 36){
            return "black";
        };
        if(point < 47){
            return "red";
        };
        return "gold";
    }

    function point_pitch(point){
        if(point < 9){
            return "0-9";
        };
        if(point < 18){
            return "9-18";
        };
        if(point < 23){
            return "18-23";
        };
        if(point < 27){
            return "23-27";
        };
        if(point < 32){
            return "27-32";
        };
        if(point < 36){
            return "32-36";
        };
        if(point < 42){
            return "36-42";
        };
        if(point < 47){
            return "42-47";
        };
        if(point < 55){
            return "47-55";
        };
        return "55+";
    }

    function create_height_graph_json(coordinates, modifier, label) {
        let colors = []
        coordinates.forEach((coord) => {
            if(label == "Difficulty"){
                colors.push(point_color(coord[3] + modifier))
            }
            if(label == "Steepness"){
                colors.push(point_pitch(coord[3] + modifier))
            }
        });

        length_of_current_color = 0;
        for(var i = 1; i < colors.length; i++){
            length_of_current_color++;
            if(colors[i - 1] != colors[i]){
                if(length_of_current_color == 1){
                    colors[i - 1] = colors[i];
                }
                else {
                    length_of_current_color = 0;  
                }
            }
        };

        let output_feature = {
            "type": "FeatureCollection",
            "features": [],
            "properties": {
                "Creator": "steepseeker.com",
                "records": 0,
                "summary": label
            }
        };
        
        let current_points = []
        for(var j = 1; j < colors.length; j++){
            current_points.push(coordinates[j])
            if(colors[j - 1] != colors[j]){
                let partial_feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": current_points
                    },
                    "properties": {
                        "attributeType": colors[j - 1]
                    }
                };
                output_feature.features.push(partial_feature);
                current_points = [coordinates[j]];
            }
        };

        let partial_feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": current_points
            },
            "properties": {
                "attributeType": colors[colors.length - 1]
            }
        };
        output_feature.features.push(partial_feature);
        output_feature.properties.records = output_feature.features.length;

        return output_feature;
    }

    function addHeightGraphData(layer) {
        let coordinates = null;
        if (layer.feature.geometry.type == "LineString") {
            coordinates = layer.feature.geometry.coordinates;
        } else if (layer.feature.properties.routeCoordinates) {
            coordinates = layer.feature.properties.routeCoordinates;
        }

        if (coordinates) {
            let difficulty_modifier = layer.feature.properties.difficulty_modifier;
            let json_data = [];
            json_data.push(create_height_graph_json(coordinates, difficulty_modifier, "Difficulty"));
            json_data.push(create_height_graph_json(coordinates, 0, "Steepness"));

            document.querySelector(".heightgraph-svg-title").textContent = layer.feature.properties.name;
            hg.addData(json_data);
        }
        else {
            document.querySelector(".heightgraph-svg-title").textContent = "Elevation Profile: N/A";
            hg.addData({})
        }
    }

    let geojson_features;

    function addTrails() {
        geojson_features = L.geoJSON(trails, {onEachFeature: onEachFeature, style: style}).addTo(map);
        map.almostOver.addLayer(geojson_features);

        geojson_features.eachLayer(function (layer) {
            layer.on("click", function () {
                if (editable && deleteMode) {
                    toggleFlag(layer);
                    return;
                }
                addHeightGraphData(layer);
            });
            if (editable && isFlagged(layer)) {
                layer.setStyle(FLAGGED_STYLE);
            }
        });
    }

    function updateTrailLabels() {
        geojson_features.removeFrom(map);
        geojson_features.removeFrom(map.almostOver);
        addTrails();
    }

    addTrails();
    map.fitBounds(geojson_features.getBounds());

    map.on('zoomend', function(){
        geojson_features.removeFrom(map);
        geojson_features.removeFrom(map.almostOver);
        addTrails();
    });

    // In delete mode a click flags the line -- suppress the bound popup
    // that Leaflet would otherwise open (covers every click path,
    // including polygons and direct layer clicks).
    map.on('popupopen', function () {
        if (editable && deleteMode) map.closePopup();
    });

    map.on('almost:over', function (e) {
        if (e.layer.feature && e.layer.feature.properties.isRoute) return;
        e.layer.setStyle({weight: 10, opacity: .7});
    });

    map.on('almost:out', function (e){
        if (e.layer.feature && e.layer.feature.properties.isRoute) return;
        if (editable && isFlagged(e.layer)) {
            e.layer.setStyle(FLAGGED_STYLE);
            return;
        }
        e.layer.setStyle({weight: 4, opacity: 1});
    });

    map.on('almost:click', function (e) {
        if (e.layer.feature && e.layer.feature.properties.isRoute) return;
        if (editable && deleteMode) {
            toggleFlag(e.layer);
            return;
        }
        e.layer.openPopup();
        const clickedLayer = e.layer;
        if (clickedLayer) {
            addHeightGraphData(clickedLayer);
        }
    });

    var legend = L.control({ position: "bottomright" });

    legend.onAdd = function(map) {
        var div = L.DomUtil.create("div", "legend");
        div.innerHTML += '<i style="background: green"></i><span>Beginner</span><br>';
        div.innerHTML += '<i style="background: royalblue"></i><span>Intermediate</span><br>';
        div.innerHTML += '<i style="background: black"></i><span>Advanced</span><br>';
        div.innerHTML += '<i style="background: red"></i><span>Expert</span><br>';
        div.innerHTML += '<i style="background: gold"></i><span>Extreme</span><br>';
        div.innerHTML += '<span>- - - Gladed</span><br>';
        return div;
    };

    legend.addTo(map);

    L.control.locate().addTo(map);

    if (editable) {
        const bulkForm = document.getElementById('bulk-delete');

        // Delete-mode toggle: while on, clicking a trail/lift line flags it
        // (orange dash-dot) instead of opening its popup. The #bulk-delete
        // form sits right below this button (adopted into a Leaflet control
        // below), shown only while the mode is on, and submits every flagged
        // id at once so the server regenerates the map/thumbnail only once.
        L.Control.DeleteModeToggle = L.Control.extend({
            onAdd: function () {
                const button = L.DomUtil.create('button');
                button.innerHTML = 'Delete Mode: Off';
                button.className = 'basemap-toggle-btn delete-mode-btn';
                L.DomEvent.disableClickPropagation(button);
                button.onclick = function () {
                    deleteMode = !deleteMode;
                    button.innerHTML = deleteMode ? 'Delete Mode: On' : 'Delete Mode: Off';
                    button.classList.toggle('active', deleteMode);
                    if (bulkForm) bulkForm.hidden = !deleteMode;
                };
                return button;
            }
        });
        L.control.deleteModeToggle = function (opts) {
            return new L.Control.DeleteModeToggle(opts);
        };
        L.control.deleteModeToggle({ position: 'topright' }).addTo(map);

        if (bulkForm) {
            // Move the (template-rendered) form into a Leaflet control so it
            // stacks directly under the Delete Mode button on the map.
            const BulkDeleteControl = L.Control.extend({
                onAdd: function () {
                    L.DomEvent.disableClickPropagation(bulkForm);
                    L.DomEvent.disableScrollPropagation(bulkForm);
                    return bulkForm;
                }
            });
            new BulkDeleteControl({ position: 'topright' }).addTo(map);

            bulkForm.addEventListener('submit', function (e) {
                bulkForm.querySelectorAll('input[name="ids"]').forEach(function (n) {
                    n.remove();
                });
                if (flagged.size === 0) {
                    e.preventDefault();
                    return;
                }
                flagged.forEach(function (id) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'ids';
                    input.value = id;
                    bulkForm.appendChild(input);
                });
            });
        }

        updateBulkDeleteForm();
    }
}
