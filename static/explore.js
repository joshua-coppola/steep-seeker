// The explore map: one marker per mountain, from the GeoJSON the page
// embeds (routes.explore_map), shown or hidden by the filters sidebar
// (filters.js, with data-apply="page") without reloading. The filters are
// read from the URL, so a shared/refreshed filtered view comes back the
// same. matchesFilters mirrors the server's own filtering
// (routes._mountain_filters + list_mountains), so the map shows the same
// mountains the search page would for the same params.
function runExploreMap (locations) {
  var map = L.map('map').setView([47.8281, -113.5795], 4)

  // corsTileLayer: see /tile-layer.js
  corsTileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Data: OSM, USGS. Tiles &copy; Esri'
  }).addTo(map)

  // an icon sized by the mountain's vertical, with its name below
  function mountainMarker (feature) {
    var p = feature.properties
    var icon = L.divIcon({
      className: 'mountain-icon',
      html:
        '<div><img src="' + p.icon + '" style="width:' + 100 * p.size + 'px;height:auto;" />' +
        '<div class="mountain-label"></div></div>',
      iconSize: [100 * p.size, 61 * p.size],
      iconAnchor: [50 * p.size, 30 * p.size],
      popupAnchor: [0, 0]
    })
    var [lng, lat] = feature.geometry.coordinates
    var marker = L.marker([lat, lng], { icon: icon }).bindPopup(p.popupContent)
    // the name as text, not markup, since it comes from OSM
    marker.on('add', function () {
      marker.getElement().querySelector('.mountain-label').textContent = p.name
    })
    return marker
  }

  var all = locations.features.map(function (feature) {
    return { feature: feature, marker: mountainMarker(feature) }
  })
  var shown = L.layerGroup().addTo(map)
  map.fitBounds(L.featureGroup(all.map(function (m) { return m.marker })).getBounds())

  // --- the filters, as the server reads them ---------------------------

  var INVALID = {}

  function numberParam (params, name, fallback) {
    var value = params.get(name)
    if (!value) return fallback
    var number = Number(value)  // "Infinity" parses, like Python's float()
    return isNaN(number) ? fallback : number
  }

  // routes._parse_state: a state's name (any case, spaces or underscores)
  // or its code; blank/"None" means no filter; anything else matches nothing
  function parseState (value) {
    if (!value || value === 'None' || value === '%%') return null
    var key = function (text) { return text.toUpperCase().replace(/ /g, '_') }
    var byName = window.US_STATES.find(function (s) { return key(s[1]) === key(value) })
    if (byName) return byName[0]
    var byCode = window.US_STATES.find(function (s) { return s[0] === value })
    return byCode ? byCode[0] : INVALID
  }

  // routes._parse_region: ignored when there's a state; "usa" or an
  // unknown region means no filter
  function parseRegion (value, state) {
    if (state) return null
    var region = window.US_REGIONS.find(function (r) {
      return r[0] === (value || 'usa').toLowerCase()
    })
    return region ? region[2] : null
  }

  // routes._parse_season_pass: a Season_Pass name, any case; anything
  // else matches nothing
  function parsePass (value) {
    if (!value) return null
    var pass = window.SEASON_PASSES.find(function (p) { return p[0] === value.toLowerCase() })
    return pass ? pass[0] : INVALID
  }

  function parseFilters (params) {
    var state = parseState(params.get('state') || params.get('location'))
    var pass = parsePass(params.get('pass'))
    if (state === INVALID || pass === INVALID) return null  // matches nothing
    return {
      state: state,
      regionStates: parseRegion(params.get('region'), state),
      pass: pass,
      difficulty: [numberParam(params, 'diffmin', 0), numberParam(params, 'diffmax', 100)],
      trails: [numberParam(params, 'trailsmin', 0), numberParam(params, 'trailsmax', 1000)],
      vertical: [numberParam(params, 'vertmin', 0), numberParam(params, 'vertmax', 100000)]
    }
  }

  function within (value, range) {
    return range[0] <= value && value <= range[1]
  }

  function matchesFilters (p, f) {
    return (
      (!f.state || p.state === f.state) &&
      (!f.regionStates || f.regionStates.indexOf(p.state) >= 0) &&
      (!f.pass || p.passes.indexOf(f.pass) >= 0) &&
      within(p.difficulty, f.difficulty) &&
      within(p.trail_count, f.trails) &&
      within(p.vertical, f.vertical)
    )
  }

  // shows just the matching mountains, leaving the view where it is
  var count = document.getElementById('match-count')
  function applyFilters (params) {
    var filters = parseFilters(params)
    shown.clearLayers()
    var matching = filters
      ? all.filter(function (m) { return matchesFilters(m.feature.properties, filters) })
      : []
    matching.forEach(function (m) { shown.addLayer(m.marker) })
    count.textContent = matching.length === all.length
      ? 'Showing all ' + all.length + ' resorts'
      : 'Showing ' + matching.length + ' of ' + all.length + ' resorts'
  }

  // --- the phone layout's Filters button, like the map pages' Details ---

  var filtersButton = document.getElementById('filtersButton')
  var sidebar = document.getElementById('sidebar')
  function setPanelOpen (open) {
    sidebar.classList.toggle('panel-open', open)
    filtersButton.classList.toggle('panel-open', open)
    filtersButton.setAttribute('aria-expanded', open)
  }
  filtersButton.addEventListener('click', function () {
    setPanelOpen(!sidebar.classList.contains('panel-open'))
  })

  applyFilters(new URLSearchParams(location.search))
  document.getElementById('filters').addEventListener('filters:apply', function (e) {
    applyFilters(e.detail)
    // on phones the filters are a panel over the map: get out of the way
    if (filtersButton.checkVisibility()) setPanelOpen(false)
  })

  var legend = L.control({ position: 'topright' })
  legend.onAdd = function () {
    var div = L.DomUtil.create('div', 'legend')
    div.innerHTML =
      '<i style="background: green"></i><span>Beginner</span><br>' +
      '<i style="background: royalblue"></i><span>Intermediate</span><br>' +
      '<i style="background: black"></i><span>Advanced</span><br>' +
      '<i style="background: red"></i><span>Expert</span><br>' +
      '<i style="background: gold"></i><span>Extreme</span><br>'
    return div
  }
  legend.addTo(map)

  L.control.locate().addTo(map)
}
