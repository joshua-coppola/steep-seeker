function run_map(trails, map){
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Data: OSM, USGS. Tiles &copy; Esri'
    }).addTo(map);

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
        heightgraph_width = window_width - 216;
    }
    if(window_width <= 500){
        heightgraph_width = window_width - 52;
        heightgraph_height = 200;
        position = "bottomright";
    }


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
            top: 10,
            right: 30,
            bottom: 55,
            left: 60
        }
    }).addTo(map);

    function onEachFeature(feature, layer) {
        // does this feature have a property named popupContent?
        if (feature.properties && feature.properties.popupContent) {
            layer.bindPopup(feature.properties.popupContent);
            if (map.getZoom() > 14) {
                layer.setText(feature.properties.label, {offset: -5, center: true, orientation: feature.properties.orientation});
            }
        }
    }

    function style(feature) {
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

    // Function to handle Heightgraph updates
    function addHeightGraphData(layer) {
        // Add elevation data for the clicked trail
        if(layer.feature.geometry.type == "LineString"){
            let difficulty_modifier = layer.feature.properties.difficulty_modifier;
            let coordinates = layer.feature.geometry.coordinates;
            let json_data = [];
            json_data.push(create_height_graph_json(coordinates, difficulty_modifier, "Difficulty"));
            json_data.push(create_height_graph_json(coordinates, 0, "Steepness"));
            
            hg.addData(json_data);
        }
        else {
            hg.addData({})
        }
    }

    function addTrails() {
        geojson_features = L.geoJSON(trails, {onEachFeature: onEachFeature, style: style}).addTo(map);
        map.almostOver.addLayer(geojson_features);

        geojson_features.eachLayer(function (layer) {
            layer.on("click", function () {
                addHeightGraphData(layer);
            });
        });
    }

    addTrails();
    map.fitBounds(geojson_features.getBounds());

    // whenever the zoom level changes, remove the layer and re-add it to 
    // force the style to update based on the current map scale
    map.on('zoomend', function(){
        geojson_features.removeFrom(map);
        geojson_features.removeFrom(map.almostOver);
        addTrails();
    });

    map.on('almost:over', function (e) {
        e.layer.setStyle({weight: 10, opacity: .7});
    });

    map.on('almost:out', function (e){
        e.layer.setStyle({weight: 4, opacity: 1});
    });

    map.on('almost:click', function (e) {
        e.layer.openPopup();
        const clickedLayer = e.layer; // The clicked trail layer
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
}