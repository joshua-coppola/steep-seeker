function run_map(trails, map, editable = false, editQuery = null){
    let deleteMode = false;
    let modifierMode = false;
    const DELETE_STYLE = {
        color: '#ff7f0e',
        weight: 7,
        opacity: 0.95,
        dashArray: '20,10,10,10',
        lineCap: 'round',
    };
    const MODIFIER_STYLE = {
        color: '#6a3d9a',
        weight: 7,
        opacity: 0.95,
        dashArray: '4,8',
        lineCap: 'round',
    };

    // Both bulk-flagging modes (delete, modifier) share the same click/
    // debounce/restyle mechanics, differing only in which ids they track
    // and which style flags them -- see makeFlagTracker.
    let lastToggle = {id: null, at: 0};

    function makeFlagTracker(style, countElementId, submitElementId) {
        const ids = new Set();

        function updateForm() {
            const count = document.getElementById(countElementId);
            if (count) count.textContent = ids.size + ' flagged';
            const submit = document.getElementById(submitElementId);
            if (submit) submit.disabled = ids.size === 0;
        }

        return {
            ids: ids,
            has: function (layer) {
                return layer.feature && ids.has(layer.feature.properties.item_id);
            },
            toggle: function (layer) {
                const id = layer.feature && layer.feature.properties.item_id;
                if (!id) return;
                const now = Date.now();
                if (lastToggle.id === id && now - lastToggle.at < 400) return;
                lastToggle = {id: id, at: now};
                if (ids.has(id)) {
                    ids.delete(id);
                    restyleLayer(layer);
                } else {
                    ids.add(id);
                    layer.setStyle(style);
                }
                updateForm();
            },
            updateForm: updateForm,
        };
    }

    const deleteFlags = makeFlagTracker(DELETE_STYLE, 'bulk-delete-count', 'bulk-delete-submit');
    const modifierFlags = makeFlagTracker(MODIFIER_STYLE, 'bulk-modifiers-count', 'bulk-modifiers-submit');

    function isTrailLayer(layer) {
        return layer.feature && layer.feature.properties.popupData &&
            layer.feature.properties.popupData.kind === 'trail';
    }

    // Dispatches a click on a trail/lift layer to whichever bulk mode is
    // active (delete flags any item; modifiers only apply to trails).
    // Returns true if the click was consumed, so callers skip their normal
    // popup/heightgraph behavior.
    function handleModeClick(layer) {
        if (!editable) return false;
        if (deleteMode) {
            deleteFlags.toggle(layer);
            return true;
        }
        if (modifierMode) {
            if (isTrailLayer(layer)) modifierFlags.toggle(layer);
            return true;
        }
        return false;
    }

    function isFlagged(layer) {
        return deleteFlags.has(layer) || modifierFlags.has(layer);
    }

    function flaggedStyle(layer) {
        if (deleteFlags.has(layer)) return DELETE_STYLE;
        if (modifierFlags.has(layer)) return MODIFIER_STYLE;
        return null;
    }

    // Sidebar-driven selection: clicking a trail/lift/hike-to row in the
    // mountain sidebar zooms to and highlights the corresponding layer.
    // Namespaced by kind since trail/lift ids aren't guaranteed distinct.
    const idToLayer = new Map();
    const featureKey = (kind, id) => kind + ':' + id;
    let selectedLayer = null;
    let selectionShadow = null;

    // An active bulk-edit flag always wins over a layer's default style --
    // it's the current admin workflow signal.
    function restyleLayer(layer) {
        if (editable && isFlagged(layer)) {
            layer.setStyle(flaggedStyle(layer));
            return;
        }
        geojson_features.resetStyle(layer);
    }

    function closeMobileSidebarIfOpen() {
        const panel = document.getElementById('mountain-details');
        if (panel && window.matchMedia('(max-width: 950px)').matches) {
            panel.style.display = 'none';
        }
    }

    // Selection is drawn as a soft glow underneath the feature's own
    // geometry -- the same wide/blurred/translucent treatment area and
    // multi-route trails already use for their route line (see
    // 'route-line-soft' in style()/interactive-map.css) -- rather than
    // recoloring the feature itself.
    function clearSelectionShadow() {
        if (selectionShadow) {
            map.removeLayer(selectionShadow);
            selectionShadow = null;
        }
    }

    const SELECTION_SHADOW_COLOR = '#00c2d1';

    function addSelectionShadow(layer) {
        const shadowStyle = {
            color: SELECTION_SHADOW_COLOR,
            weight: 16,
            opacity: 0.25,
            interactive: false,
            lineCap: 'round',
            lineJoin: 'round',
            className: 'route-line-soft',
            fill: false,
        };
        selectionShadow = layer instanceof L.Polygon
            ? L.polygon(layer.getLatLngs(), shadowStyle)
            : L.polyline(layer.getLatLngs(), shadowStyle);
        selectionShadow.addTo(map);
    }

    function selectFeature(kind, id) {
        const layer = idToLayer.get(featureKey(kind, id));
        if (!layer) return;
        map.closePopup();
        selectedLayer = layer;
        clearSelectionShadow();
        addSelectionShadow(layer);
        const bounds = layer.getBounds();
        const opts = {maxZoom: 17, padding: [40, 40]};
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            map.fitBounds(bounds, opts);
        } else {
            map.flyToBounds(bounds, {...opts, duration: 0.75});
        }
        closeMobileSidebarIfOpen();
    }

    function clearSelection() {
        if (!selectedLayer) return;
        selectedLayer = null;
        clearSelectionShadow();
    }

    document.addEventListener('click', function (e) {
        const item = e.target.closest('.sidebar-item');
        if (!item) return;
        selectFeature(item.dataset.kind, item.dataset.itemId);
    });

    // Define two basemaps
    const topoBasemap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: 'Data: OSM, USGS. Tiles &copy; Esri'
    });

    const satelliteBasemap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
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
            L.DomEvent.disableClickPropagation(button);

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

    function escapeAttr(value) {
        // escapeHtml alone doesn't escape quotes, since those are only
        // unsafe in an attribute-value context, not in text content.
        return escapeHtml(value).replace(/"/g, '&quot;');
    }

    function buildDeleteFormHtml(id) {
        const q = escapeAttr(editQuery);
        return (
            '<form id="delete" class="search-form">' +
            `<input type="hidden" name="q" value="${q}">` +
            `<input type="hidden" name="delete" value="${escapeAttr(id)}">` +
            '<span class="checkbox-group">' +
            '<input type="checkbox" id="blacklist" name="blacklist" value=True>' +
            '<label for="blacklist">Blacklist</label>' +
            '</span>' +
            '<input class="button-cta" id="delete_submit" type="submit" value="Delete" /></form>'
        );
    }

    function buildTrailEditFormsHtml(id, data) {
        const q = escapeAttr(editQuery);
        const gladedChecked = data.gladed ? 'checked' : '';
        const ungroomedChecked = data.ungroomed ? 'checked' : '';
        const hazardousChecked = data.hazardous ? 'checked' : '';
        return (
            '<form id="update_tags" class="search-form">' +
            `<input type="hidden" name="q" value="${q}">` +
            `<input type="hidden" name="trail_id" value="${escapeAttr(id)}">` +
            '<span class="checkbox-group">' +
            `<input type="checkbox" id="gladed" name="gladed" value=True ${gladedChecked}>` +
            '<label for="gladed">Gladed</label>' +
            '</span>' +
            '<span class="checkbox-group">' +
            `<input type="checkbox" id="ungroomed" name="ungroomed" value=True ${ungroomedChecked}>` +
            '<label for="ungroomed">Ungroomed</label>' +
            '</span>' +
            '<span class="checkbox-group">' +
            `<input type="checkbox" id="hazardous" name="hazardous" value=True ${hazardousChecked}>` +
            '<label for="hazardous">Hazardous</label>' +
            '</span>' +
            '<input class="button-cta" id="update_tags_submit" type="submit" value="Update" /></form>'
        ) + buildDeleteFormHtml(id);
    }

    function buildTrailPopupHtml(data, id) {
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
        if (editable) html += buildTrailEditFormsHtml(id, data);
        return html;
    }

    function buildLiftPopupHtml(data, id) {
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
        if (editable) html += buildDeleteFormHtml(id);
        return html;
    }

    function labelAttributes() {
        const textColor = currentBasemap === 'satellite' ? 'white' : 'black';
        const haloColor = currentBasemap === 'satellite' ? satelliteLabelHalo : 'white';
        // +3px per zoom level above 15, where labels first appear at the
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

    // Matches trail_color() in core/support/utils.py -- glyph shapes mirror
    // the site's standard difficulty icons (circle/square/diamond).
    const RATING_GLYPHS = {
        green: {glyph: '●', fill: 'green'},
        royalblue: {glyph: '■', fill: 'royalblue'},
        black: {glyph: '◆', fill: 'black'},
        red: {glyph: '◆◆', fill: 'red', letterSpacing: '-0.15em'},
        gold: {glyph: '◆◆', fill: 'gold', letterSpacing: '-0.15em'},
    };

    function ratingRun(feature) {
        // Lifts get color: 'grey' (not a key here), so they're naturally
        // excluded -- no need to check popupData.kind, which an area/
        // multi-route trail's route-label feature doesn't carry (see
        // _trail_features in routes.py).
        return RATING_GLYPHS[feature.properties.color] || null;
    }

    function applyLabel(layer, feature) {
        if (!feature.properties || !feature.properties.label) return;
        layer.setText(null);
        if (map.getZoom() > 14) {
            const rating = ratingRun(feature);
            const iconAttributes = rating && rating.letterSpacing
                ? {fill: rating.fill, 'letter-spacing': rating.letterSpacing}
                : rating && {fill: rating.fill};
            const text = rating
                ? [
                    {text: rating.glyph, attributes: iconAttributes},
                    {text: feature.properties.label, attributes: {dx: '0.15em'}},
                ]
                : feature.properties.label;
            layer.setText(text, {
                offset: -5,
                center: true,
                orientation: feature.properties.orientation,
                attributes: labelAttributes(),
                refreshAttributes: labelAttributes
            });
        }
    }

    function onEachFeature(feature, layer) {
        if (feature.properties && feature.properties.popupData) {
            // Built lazily -- only when a popup is actually opened -- since
            // most of a resort's 600+ trails/lifts never get clicked in a
            // given visit.
            layer.bindPopup(function () {
                const data = feature.properties.popupData;
                const id = feature.properties.item_id;
                return data.kind === 'lift' ? buildLiftPopupHtml(data, id) : buildTrailPopupHtml(data, id);
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
                if (handleModeClick(layer)) return;
                addHeightGraphData(layer);
            });
            if (editable && isFlagged(layer)) {
                layer.setStyle(flaggedStyle(layer));
            }
            const props = layer.feature && layer.feature.properties;
            if (props && props.item_id && props.popupData) {
                idToLayer.set(featureKey(props.popupData.kind, props.item_id), layer);
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
    // fitBounds changes the zoom after labels were computed at the map's
    // initial zoom (13, set in the template) -- resync now so labels drawn
    // above/below the zoom-14 threshold reflect where the map actually lands.
    updateTrailLabels();

    // A trail/lift rankings row can deep-link here with e.g.
    // ?select=trail:w123 -- reuse the same sidebar selection machinery so
    // the map lands zoomed in on and highlighting that specific feature
    // instead of the whole resort.
    const selectParam = new URLSearchParams(window.location.search).get('select');
    if (selectParam) {
        const [selectKind, selectId] = selectParam.split(':');
        if (selectKind && selectId) selectFeature(selectKind, selectId);
    }

    map.on('dragstart', function () { map.almostOver.disable(); });
    map.on('dragend', function () { map.almostOver.enable(); });

    // leaflet.textpath rebuilds every label's DOM node (forcing a
    // synchronous layout per label via getComputedTextLength()/getBBox())
    // on every moveend. Hide
    // labels for the duration of an actual drag and defer the real
    // rebuild until movement has fully settled (including post-drag
    // inertia), so a rapid sequence of pans only rebuilds once. Scoped to
    // 'dragstart' rather than 'movestart' so a plain zoom (already
    // handled below) is never double-rebuilt.
    let panLabelsHidden = false;
    let panSettleTimer = null;
    let labelFadeTimer = null;
    const PAN_SETTLE_MS = 200;
    const LABEL_FADE_MS = 150; // matches interactive-map.css's transition duration

    function removeFadedLabels() {
        geojson_features.eachLayer(function (layer) {
            if (layer.feature) layer.setText(null);
        });
    }

    map.on('dragstart', function () {
        panLabelsHidden = true;
        if (panSettleTimer) {
            clearTimeout(panSettleTimer);
            panSettleTimer = null;
        }
        geojson_features.eachLayer(function (layer) {
            if (layer.feature && layer._textNode) layer._textNode.style.opacity = '0';
        });
        if (labelFadeTimer) clearTimeout(labelFadeTimer);
        labelFadeTimer = setTimeout(function () {
            labelFadeTimer = null;
            removeFadedLabels();
        }, LABEL_FADE_MS);
    });
    map.on('moveend', function () {
        if (!panLabelsHidden) return;
        if (panSettleTimer) clearTimeout(panSettleTimer);
        panSettleTimer = setTimeout(function () {
            panSettleTimer = null;
            panLabelsHidden = false;
            updateTrailLabels();
        }, PAN_SETTLE_MS);
    });

    let labelsShown = map.getZoom() > 14;
    map.on('zoomend', function () {
        const shouldShow = map.getZoom() > 14;
        if (shouldShow === labelsShown) return;
        labelsShown = shouldShow;
        updateTrailLabels();
    });

    map.on('popupopen', function () {
        if (editable && (deleteMode || modifierMode)) map.closePopup();
    });

    map.on('click', function () { clearSelection(); });

    map.on('almost:over', function (e) {
        if (e.layer.feature && e.layer.feature.properties.isRoute) return;
        e.layer.setStyle({weight: 10, opacity: .7});
    });

    map.on('almost:out', function (e){
        if (e.layer.feature && e.layer.feature.properties.isRoute) return;
        restyleLayer(e.layer);
    });

    map.on('almost:click', function (e) {
        if (e.layer.feature && e.layer.feature.properties.isRoute) return;
        if (handleModeClick(e.layer)) return;
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
        L.DomEvent.disableClickPropagation(div);
        return div;
    };

    legend.addTo(map);

    L.control.locate().addTo(map);

    if (editable) {
        const deleteForm = document.getElementById('bulk-delete');
        const modifierForm = document.getElementById('bulk-modifiers');
        let deleteButton, modifierButton;

        // Delete Mode and Modifier Mode are mutually exclusive -- turning
        // one on always forces the other off (button label/style + its
        // form's visibility), though a mode's own flags are kept when it's
        // toggled off (either manually or by the other mode taking over),
        // so switching back to it resumes where you left off.
        function setDeleteMode(on) {
            deleteMode = on;
            deleteButton.innerHTML = 'Delete Mode: ' + (on ? 'On' : 'Off');
            deleteButton.classList.toggle('active', on);
            if (deleteForm) deleteForm.hidden = !on;
        }

        function setModifierMode(on) {
            modifierMode = on;
            modifierButton.innerHTML = 'Modifier Mode: ' + (on ? 'On' : 'Off');
            modifierButton.classList.toggle('active', on);
            if (modifierForm) modifierForm.hidden = !on;
        }

        function toggleDeleteMode() {
            setDeleteMode(!deleteMode);
            if (deleteMode) setModifierMode(false);
        }

        function toggleModifierMode() {
            setModifierMode(!modifierMode);
            if (modifierMode) setDeleteMode(false);
        }

        function addModeButton(className, label, onClick) {
            const ToggleControl = L.Control.extend({
                onAdd: function () {
                    const button = L.DomUtil.create('button');
                    button.innerHTML = label + ': Off';
                    button.className = 'basemap-toggle-btn ' + className;
                    L.DomEvent.disableClickPropagation(button);
                    button.onclick = onClick;
                    return button;
                }
            });
            return new ToggleControl({ position: 'topright' }).addTo(map).getContainer();
        }

        deleteButton = addModeButton('delete-mode-btn', 'Delete Mode', toggleDeleteMode);
        modifierButton = addModeButton('modifier-mode-btn', 'Modifier Mode', toggleModifierMode);

        // Wires a (template-rendered) bulk form's submit to inject one
        // hidden "ids" input per flagged id, and moves it into a Leaflet
        // control so it stacks under the mode toggle buttons on the map.
        function wireBulkForm(form, flagTracker) {
            if (!form) return;

            const BulkFormControl = L.Control.extend({
                onAdd: function () {
                    L.DomEvent.disableClickPropagation(form);
                    L.DomEvent.disableScrollPropagation(form);
                    return form;
                }
            });
            new BulkFormControl({ position: 'topright' }).addTo(map);

            form.addEventListener('submit', function (e) {
                form.querySelectorAll('input[name="ids"]').forEach(function (n) {
                    n.remove();
                });
                if (flagTracker.ids.size === 0) {
                    e.preventDefault();
                    return;
                }
                flagTracker.ids.forEach(function (id) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'ids';
                    input.value = id;
                    form.appendChild(input);
                });
            });
        }

        wireBulkForm(deleteForm, deleteFlags);
        wireBulkForm(modifierForm, modifierFlags);

        deleteFlags.updateForm();
        modifierFlags.updateForm();
    }
}
