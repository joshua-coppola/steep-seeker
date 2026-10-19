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
    // feature-sheet behavior.
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
        openFeatureSheet(layer);
        // Fit the feature into the part of the map left visible under the
        // sheet: zoom to fit (map minus sheet, plus 40px margins) and
        // shift it down by half the sheet's height.
        const bounds = layer.getBounds();
        const sheetBottom = featureSheetBottom();
        const zoom = Math.min(17, map.getBoundsZoom(bounds, false, L.point(80, 80 + sheetBottom)));
        const center = centerForOffset(bounds.getCenter(), L.point(0, sheetBottom / 2), zoom);
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            map.setView(center, zoom);
        } else {
            map.flyTo(center, zoom, {duration: 0.75});
        }
        closeMobileSidebarIfOpen();
    }

    // The map center that, at `zoom`, puts `latlng` at `offset` screen
    // pixels from the middle of the map. Worked out from
    // containerPointToLatLng() (which honors the map's bearing) rather than
    // Leaflet's padding options/panInside(), which leaflet-rotate applies in
    // the unrotated frame -- pushing the feature sideways (or off-screen) on
    // a rotated resort.
    // (A screen-pixel offset is the same number of world pixels at every
    // zoom, so the offset measured at the current zoom applies as-is.)
    function centerForOffset(latlng, offset, zoom) {
        const mid = map.getSize().divideBy(2);
        const worldOffset = map.project(map.containerPointToLatLng(mid.add(offset)))
            .subtract(map.project(map.containerPointToLatLng(mid)));
        return map.unproject(map.project(latlng, zoom).subtract(worldOffset), zoom);
    }

    // Selecting a feature and showing its sheet always go together, so
    // clearing the selection also closes the sheet.
    function clearSelection() {
        closeFeatureSheet();
        if (!selectedLayer) return;
        selectedLayer = null;
        clearSelectionShadow();
    }

    document.addEventListener('click', function (e) {
        const item = e.target.closest('.sidebar-item');
        if (!item) return;
        selectFeature(item.dataset.kind, item.dataset.itemId);
    });

    // Define two basemaps (corsTileLayer: see /tile-layer.js)
    const topoBasemap = corsTileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: 'Data: OSM, USGS. Tiles &copy; Esri'
    });

    const satelliteBasemap = corsTileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
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

    // Clicking a trail/lift opens a sheet docked to the top of the map that
    // holds both its elevation profile and its stats (formerly a separate
    // floating heightgraph control and a Leaflet popup). It's built here,
    // inside the map container, so it lines up with #map on every page
    // that calls run_map regardless of that page's header height. It sizes
    // to its content (management mode's edit forms make it much taller)
    // and its width is capped on desktop, and the top Leaflet control
    // corners are pushed down below it via --feature-sheet-offset[-right]
    // (see interactive-map.css).
    const sheet = L.DomUtil.create('section', 'feature-sheet', map.getContainer());
    sheet.hidden = true;
    sheet.innerHTML =
        '<header class="feature-sheet-header">' +
        '<h3 class="feature-sheet-title"></h3>' +
        '<button type="button" class="feature-sheet-close" aria-label="Close">&times;</button>' +
        '</header>' +
        '<div class="feature-sheet-graph"></div>' +
        '<div class="feature-sheet-stats"></div>' +
        '<div class="feature-sheet-admin"></div>';
    L.DomEvent.disableClickPropagation(sheet);
    L.DomEvent.disableScrollPropagation(sheet);
    const sheetTitle = sheet.querySelector('.feature-sheet-title');
    const sheetGraph = sheet.querySelector('.feature-sheet-graph');
    const sheetStats = sheet.querySelector('.feature-sheet-stats');
    const sheetAdmin = sheet.querySelector('.feature-sheet-admin');
    sheet.querySelector('.feature-sheet-close').addEventListener('click', function () {
        clearSelection();
    });

    // Gap between the sheet and the controls pushed below it, matching
    // Leaflet's own .leaflet-control margin.
    const SHEET_GAP = 10;

    // The top-left corner always sits under the sheet; the top-right one
    // only does when the map is too narrow for the width-capped sheet and
    // that corner's controls to fit side by side, so it's only pushed down
    // then. Re-checked whenever either one resizes (the management page's
    // bulk forms widen the right corner when a mode is toggled on).
    const container = map.getContainer();
    const rightCorner = container.querySelector('.leaflet-top.leaflet-right');

    function updateControlOffsets() {
        const height = sheet.offsetHeight;
        const offset = height ? (height + SHEET_GAP) + 'px' : '0px';
        const overlapsRight = height &&
            sheet.offsetLeft + sheet.offsetWidth + SHEET_GAP > rightCorner.offsetLeft;
        container.style.setProperty('--feature-sheet-offset', offset);
        container.style.setProperty('--feature-sheet-offset-right', overlapsRight ? offset : '0px');
    }

    const controlOffsetObserver = new ResizeObserver(updateControlOffsets);
    controlOffsetObserver.observe(sheet);
    controlOffsetObserver.observe(rightCorner);
    controlOffsetObserver.observe(container);

    // Bottom edge of the sheet in map-container pixels (0 when closed), for
    // keeping the selected feature from landing underneath it.
    function featureSheetBottom() {
        return sheet.hidden ? 0 : sheet.offsetTop + sheet.offsetHeight;
    }

    // Breakpoints match the site's own: 950px (desktop vs. mobile layout,
    // see map_shared.css) and 500px (phones).
    function heightgraphHeight() {
        if (window.matchMedia('(max-width: 500px)').matches) return 130;
        if (window.matchMedia('(max-width: 950px)').matches) return 160;
        return 200;
    }

    const hg = L.control.heightgraph({
        mappings: colorMappings,
        graphStyle: {
            opacity: 0.8,
            'fill-opacity': 0.5,
            'stroke-width': '2px'
        },
        // The sheet's own open/close replaces the control's expand toggle.
        expandControls: false,
        expand: true,
        width: 300,
        height: heightgraphHeight(),
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
            // room for the last x-axis tick label (e.g. "1476 ft"), which
            // is centered on the axis's right end
            right: 30,
            bottom: 40,
            left: 60
        }
    }).addTo(map);
    // Still added to the map (it draws its hover marker/highlight there),
    // but its DOM lives in the sheet rather than a control corner.
    sheetGraph.appendChild(hg.getContainer());

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

    function formatFeet(value) {
        return value == null ? '–' : Number(value).toLocaleString('en-US') + ' ft';
    }

    // Stats layout shared by trails and lifts: a summary line of headline
    // facts (led by a rating badge for trails), then a row of small cards
    // -- trails: one per steepest-pitch window, edged in that pitch's
    // difficulty color; lifts: type/seats/amenities. Styled after the
    // site's buttons and rankings (see .sheet-chip in interactive-map.css).
    function sheetFactHtml(value, label) {
        return `<span class="sheet-fact">${value} <span class="sheet-muted">${label}</span></span>`;
    }

    function sheetChipHtml(label, valueHtml, color) {
        const colorClass = color ? ` chip-${color}` : '';
        return (
            `<div class="sheet-chip${colorClass}">` +
            `<span class="sheet-chip-label">${label}</span>` +
            `<span class="sheet-chip-value">${valueHtml}</span>` +
            '</div>'
        );
    }

    // Icon first, then value -- how the rankings tables write difficulty.
    function difficultyValueHtml(value, color, suffix) {
        return `<span class="icon difficulty-${color}"></span>${value}${suffix || ''}`;
    }

    function debugIdHtml(label, id) {
        return id ? `<p class="sheet-debug sheet-muted">${label} ID: ${escapeHtml(id)}</p>` : '';
    }

    // Each sheet builder returns its title (h3 contents), stats and, in
    // management mode, admin forms as separate HTML so they land in their
    // own regions of the sheet.
    function buildTrailSheetHtml(data, id) {
        let badges = '';
        if (data.gladed) badges += '<i class="icon gladed" title="Gladed"></i>';
        if (data.ungroomed) badges += '<i class="icon ungroomed" title="Ungroomed/Moguls"></i>';
        if (data.hazardous) badges += '<i class="icon hazardous" title="Hazardous"></i>';

        const level = colorMappings.Difficulty[data.color];
        let html = '<div class="sheet-summary">';
        html += (
            `<span class="sheet-rating chip-${data.color}">` +
            difficultyValueHtml(data.difficulty, data.color) +
            (level ? ` <span class="sheet-rating-level">${level.text}</span>` : '') +
            '</span>'
        );
        html += sheetFactHtml(formatFeet(data.length_feet), 'long');
        html += sheetFactHtml('&darr; ' + formatFeet(data.vertical_feet), 'vertical');
        html += '</div>';

        if (data.pitches.length) {
            html += '<p class="sheet-section-label">Steepest pitch over</p>';
            html += '<div class="sheet-chips">';
            data.pitches.forEach(function (pitch) {
                html += sheetChipHtml(
                    pitch.label, difficultyValueHtml(pitch.value, pitch.color, '°'), pitch.color
                );
            });
            html += '</div>';
        }
        html += debugIdHtml('Trail', data.debug_id);
        return {
            title: escapeHtml(data.name) + badges,
            stats: html,
            admin: editable ? buildTrailEditFormsHtml(id, data) : '',
        };
    }

    function buildLiftSheetHtml(data, id) {
        let html = '<div class="sheet-summary">';
        html += sheetFactHtml(formatFeet(data.length_feet), 'long');
        html += sheetFactHtml('&uarr; ' + formatFeet(data.vertical_feet), 'vertical');
        html += sheetFactHtml(`${data.average_slope}°`, 'avg pitch');
        html += '</div>';

        html += '<div class="sheet-chips sheet-chips-auto">';
        html += sheetChipHtml('Type', escapeHtml(data.lift_type_label));
        if (data.occupancy) {
            const seats = data.occupancy <= 4
                ? '<span class="icon person"></span>'.repeat(data.occupancy)
                : `${data.occupancy}<span class="small-spacer"></span><span class="icon person"></span>`;
            html += sheetChipHtml('Seats', seats);
        }
        if (data.bubble) html += sheetChipHtml('Bubble', 'Yes');
        if (data.heating) html += sheetChipHtml('Heated', 'Yes');
        html += '</div>';
        html += debugIdHtml('Lift', data.debug_id);
        return {
            title: escapeHtml(data.name),
            stats: html,
            admin: editable ? buildDeleteFormHtml(id) : '',
        };
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

    // Draws the layer's profile into the sheet's heightgraph. Returns false
    // (leaving the graph hidden) for features with no elevation profile,
    // e.g. an area trail without a computed route.
    function addHeightGraphData(layer) {
        let coordinates = null;
        if (layer.feature.geometry.type == "LineString") {
            coordinates = layer.feature.geometry.coordinates;
        } else if (layer.feature.properties.routeCoordinates) {
            coordinates = layer.feature.properties.routeCoordinates;
        }
        if (!coordinates) return false;

        let difficulty_modifier = layer.feature.properties.difficulty_modifier;
        let json_data = [];
        json_data.push(create_height_graph_json(coordinates, difficulty_modifier, "Difficulty"));
        json_data.push(create_height_graph_json(coordinates, 0, "Steepness"));

        // The sheet's width varies by viewport (and the sheet was hidden
        // until just now), so size the graph to it on every open -- set
        // directly rather than via hg.resize(), which would redraw the
        // previous feature's data first.
        hg.options.width = sheetGraph.clientWidth;
        hg.options.height = heightgraphHeight();
        hg.getContainer().querySelectorAll('svg').forEach(function (svg) {
            svg.setAttribute('width', hg.options.width);
            svg.setAttribute('height', hg.options.height);
        });
        hg.addData(json_data);
        return true;
    }

    function openFeatureSheet(layer) {
        const data = layer.feature && layer.feature.properties.popupData;
        if (!data) return;
        const parts = data.kind === 'lift'
            ? buildLiftSheetHtml(data, layer.feature.properties.item_id)
            : buildTrailSheetHtml(data, layer.feature.properties.item_id);
        sheetTitle.innerHTML = parts.title;
        sheetStats.innerHTML = parts.stats;
        sheetAdmin.innerHTML = parts.admin;
        sheetAdmin.hidden = !parts.admin;
        sheet.hidden = false;
        clearHeightgraphMarker();
        sheetGraph.hidden = false;
        sheetGraph.hidden = !addHeightGraphData(layer);

        selectedLayer = layer;
        clearSelectionShadow();
        addSelectionShadow(layer);
    }

    // The heightgraph draws its position marker (dot/line/elevation label)
    // straight into the map's overlay SVG and only hides it on a mouseout
    // from the chart -- which never comes if the sheet closes or switches
    // features first, or on a touch device. mapMouseoutHandler(0) is the
    // control's own (public) way to hide it.
    function clearHeightgraphMarker() {
        hg.mapMouseoutHandler(0);
    }

    function closeFeatureSheet() {
        if (sheet.hidden) return;
        sheet.hidden = true;
        clearHeightgraphMarker();
        // Clears the heightgraph's drag-selected segments from the map
        // along with the chart itself.
        hg.addData({});
    }

    // A click on a feature also bubbles to the map's own 'click' (which
    // closes the sheet), and both the layer's direct click and AlmostOver's
    // near-miss 'almost:click' can fire for the same physical click -- this
    // flag, set for the rest of the click's dispatch, lets the map handler
    // tell the two cases apart.
    let featureClickInProgress = false;

    function onFeatureClick(layer, latlng) {
        featureClickInProgress = true;
        setTimeout(function () { featureClickInProgress = false; });
        if (handleModeClick(layer)) return;
        if (layer === selectedLayer && !sheet.hidden) return;
        openFeatureSheet(layer);
        if (!latlng || sheet.hidden) return;
        // If the clicked spot is now under the sheet, pan it just below.
        const point = map.latLngToContainerPoint(latlng);
        const minY = featureSheetBottom() + 40;
        if (point.y >= minY) return;
        const mid = map.getSize().divideBy(2);
        map.panTo(centerForOffset(latlng, L.point(point.x - mid.x, minY - mid.y), map.getZoom()));
    }

    window.addEventListener('resize', function () {
        if (sheet.hidden || sheetGraph.hidden) return;
        hg.resize({width: sheetGraph.clientWidth, height: heightgraphHeight()});
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') clearSelection();
    });

    let geojson_features;

    function addTrails() {
        geojson_features = L.geoJSON(trails, {onEachFeature: onEachFeature, style: style}).addTo(map);
        map.almostOver.addLayer(geojson_features);

        geojson_features.eachLayer(function (layer) {
            layer.on("click", function (e) {
                onFeatureClick(layer, e.latlng);
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

    map.on('click', function () {
        if (featureClickInProgress) return;
        clearSelection();
    });

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
        onFeatureClick(e.layer, e.latlng);
    });

    
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
