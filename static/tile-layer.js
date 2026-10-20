// Leaflet tile layers that load as CORS requests when possible, falling back to
// plain image requests if the browser blocks cross-origin requests (e.g. a
// privacy setting or extension).
//
// CORS tiles are preferred because the service worker can then cache them as
// normal responses; non-CORS tiles come back opaque, which browsers count as
// several MB each against the storage quota.
(function () {
  var STORAGE_KEY = 'corsTilesBlocked';
  var layers = [];

  function readBlocked() {
    try {
      return sessionStorage.getItem(STORAGE_KEY) === 'true';
    } catch (error) {
      return false;
    }
  }

  // remembered for the session so later map pages skip straight to plain
  // tiles instead of each failing a tile first
  var corsBlocked = readBlocked();

  function fallBackToPlainTiles() {
    if (corsBlocked) {
      return;
    }
    corsBlocked = true;
    try {
      sessionStorage.setItem(STORAGE_KEY, 'true');
    } catch (error) {
      // storage unavailable: the fallback still applies to this page
    }
    layers.forEach(function (layer) {
      layer.options.crossOrigin = false;
      // redraw() only re-requests tiles for layers currently on the map;
      // the others pick up the new option when they're next added
      if (layer._map) {
        layer.redraw();
      }
    });
  }

  window.corsTileLayer = function (url, options) {
    var layer = L.tileLayer(url, Object.assign({}, options, { crossOrigin: !corsBlocked }));
    layers.push(layer);
    layer.on('tileerror', function () {
      // an offline failure isn't a CORS problem; leave the layer alone so it
      // keeps caching CORS tiles once the connection is back
      if (navigator.onLine) {
        fallBackToPlainTiles();
      }
    });
    return layer;
  };
})();
