function run_map(trails, map, editable = false){
    let deleteMode = false;
    const flagged = new Set();
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

    const satelliteLabelHalo = getComputedStyle(document.body).getPropertyValue('--color-secondary').trim() || '#666';
    
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

    function escapeHtml(value) {
        const div = document.createElement('div');
        div.textContent = value == null ? '' : String(value);
        return div.innerHTML;
    }

    function buildTrailPopupHtml(data) {
        let badges = '';
        if (data.gladed) badges += '<i class="icon gladed"></i>';
        if (data.ungroomed) badges += '<i class="icon ungroomed"></i>';
        if (data.hazardous) badges += '<i class="icon hazardous"></i>';

        let html = `<h3>${escapeHtml(data.name)}${badges}</h3>`;
        html += `<p>Rating: ${data.difficulty}<span class="icon difficulty-${data.color}"></span></p>`;
        html += `<p>Length: ${data.length_feet} ft</p>`;
        html += `<p>Vertical Drop: ${data.vertical_feet} ft</p>`;
        data.pitches.forEach(function (pitch) {
            html += `<p>${pitch.label} Pitch: ${pitch.value}°<span class="icon difficulty-${pitch.color}"></span></p>`;
        });
        if (data.debug_id) {
            html += `<p>Trail ID: ${escapeHtml(data.debug_id)}</p>`;
        }
        return html;
    }

    function buildLiftPopupHtml(data) {
        let html = `<h3>${escapeHtml(data.name)}</h3>`;
        if (data.occupancy) {
            if (data.occupancy <= 4) {
                html += '<p>' + '<span class="icon person"></span>'.repeat(data.occupancy) + '</p>';
            } else {
                html += `<p class="occupancy">${data.occupancy}<span class="small-spacer"></span><span class="icon person"></span></p>`;
            }
        }
        html += `<p>Type: ${escapeHtml(data.lift_type_label)}</p>`;
        html += `<p>Length: ${data.length_feet} ft</p>`;
        html += `<p>Vertical Rise: ${data.vertical_feet} ft</p>`;
        html += `<p>Average Pitch: ${data.average_slope}°</p>`;
        if (data.bubble) html += '<p>&#x2705; Bubble</p>';
        if (data.heating) html += '<p>&#x2705; Heated</p>';
        if (data.debug_id) {
            html += `<p>Lift ID: ${escapeHtml(data.debug_id)}</p>`;
        }
        return html;
    }

    function labelAttributes() {
        const textColor = currentBasemap === 'satellite' ? 'white' : 'black';
        const haloColor = currentBasemap === 'satellite' ? satelliteLabelHalo : 'white';
        // +1px per zoom level above 15, where labels first appear at the
        // base 14px.
        const fontSize = 14 + (Math.max(0, map.getZoom() - 15) * 3);
        return {
            fill: textColor,
            'font-size': fontSize + 'px',
            stroke: haloColor,
            'stroke-width': '3px',
            'stroke-linejoin': 'round',
            'paint-order': 'stroke fill'
        };
    }

    function applyLabel(layer, feature) {
        if (!feature.properties || !feature.properties.label) return;
        layer.setText(null);
        if (map.getZoom() > 14) {
            layer.setText(feature.properties.label, {
                offset: -5,
                center: true,
                orientation: feature.properties.orientation,
                attributes: labelAttributes(),
                refreshAttributes: labelAttributes
            });
        }
    }

    function onEachFeature(feature, layer) {
        if (feature.properties && feature.properties.popupContent) {
            layer.bindPopup(feature.properties.popupContent);
        } else if (feature.properties && feature.properties.popupData) {
            // Built lazily -- only when a popup is actually opened -- since
            // most of a resort's 600+ trails/lifts never get clicked in a
            // given visit.
            layer.bindPopup(function () {
                const data = feature.properties.popupData;
                return data.kind === 'lift' ? buildLiftPopupHtml(data) : buildTrailPopupHtml(data);
            });
        }
        applyLabel(layer, feature);
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
        if (feature.properties.lift_type == 'hike') {
            return {color: feature.properties.color, weight: 4, dashArray: '1,6', lineCap: 'round'}
        }
        return {color: feature.properties.color, weight: 4}
    }

    function point_color(point) {
        var k = window.DIFFICULTY_CONSTANTS;
        if(point < k.beginner_max){
            return "green";
        };
        if(point < k.intermediate_max){
            return "royalblue";
        };
        if(point < k.advanced_max){
            return "black";
        };
        if(point < k.expert_max){
            return "red";
        };
        return "gold";
    }

    function point_pitch(point){
        // matches the bands buildSteepnessMapping (mappings.js) builds,
        // from the same steepnessBoundaries()
        var bounds = steepnessBoundaries();
        for (var i = 0; i < bounds.length; i++) {
            if (point < bounds[i]) {
                return (i === 0 ? 0 : bounds[i - 1]) + "-" + bounds[i];
            }
        }
        return bounds[bounds.length - 1] + "+";
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
        geojson_features.eachLayer(function (layer) {
            if (layer.feature) applyLabel(layer, layer.feature);
        });
    }

    map.invalidateSize();

    addTrails();
    map.fitBounds(geojson_features.getBounds());

    map.on('dragstart', function () { map.almostOver.disable(); });
    map.on('dragend', function () { map.almostOver.enable(); });

    let labelsShown = map.getZoom() > 14;
    map.on('zoomend', function () {
        const shouldShow = map.getZoom() > 14;
        if (shouldShow === labelsShown) return;
        labelsShown = shouldShow;
        updateTrailLabels();
    });

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
