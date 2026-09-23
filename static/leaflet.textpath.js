/*
 * Leaflet.TextPath - Shows text along a polyline
 * Inspired by Tom Mac Wright article :
 * https://web.archive.org/web/20130312131812/http://mapbox.com/osmdev/2012/11/20/getting-serious-about-svg/
 */

(function () {

var __onAdd = L.Polyline.prototype.onAdd,
    __onRemove = L.Polyline.prototype.onRemove,
    __updatePath = L.Polyline.prototype._updatePath,
    __bringToFront = L.Polyline.prototype.bringToFront;

/* Leaflet's SVG renderer always emits path data as "M{x} {y}L{x} {y}L..."
   (see pointsToPath in leaflet's SVG.Util.js) -- parse that back into raw
   [x,y] points for the helpers below. */
function parsePathPoints(d) {
    var nums = d.match(/-?\d+\.?\d*/g) || [];
    var points = [];
    for (var i = 0; i < nums.length; i += 2) {
        points.push([parseFloat(nums[i]), parseFloat(nums[i + 1])]);
    }
    return points;
}

function pointsToD(points) {
    return points.map(function (p, i) { return (i ? 'L' : 'M') + p[0] + ' ' + p[1]; }).join('');
}

/* Drops points closer together than MIN_POINT_SPACING (except the
   endpoints). SVG's textPath places each glyph as a rigid shape following
   the tangent at a single sampled point; a run of points closer together
   than a glyph is wide gives consecutive glyphs almost the same
   tangent-sample spacing as their own width, so they overlap. This is only
   visible walking a path backwards -- forward rendering of the same dense
   points (e.g. a catwalk with many closely-surveyed OSM nodes) is fine --
   so it's corrected only when reversing, rather than for every path. */
var MIN_POINT_SPACING = 15;
function decimate(points) {
    if (points.length < 3) return points.slice();
    var kept = [points[0]];
    for (var j = 1; j < points.length - 1; j++) {
        var last = kept[kept.length - 1];
        var dx = points[j][0] - last[0], dy = points[j][1] - last[1];
        if (Math.sqrt(dx * dx + dy * dy) >= MIN_POINT_SPACING) kept.push(points[j]);
    }
    kept.push(points[points.length - 1]);
    return kept;
}

function reversePoints(points) {
    return decimate(points).reverse();
}

/* Mirrors _get_label_placement in maps.py, which picks the straightest run
   of a trail long enough to fit its label on the static map images --
   rather than always dead-centering the label on the whole path, which can
   land it mid-label in a sharp bend. Returns the winning run's own points
   (forward order), its length (in the same units as path.getTotalLength()),
   and its mean local bearing in degrees (atan2 of consecutive points, so
   0 = the path's own +x direction).

   Ties (including the common case of a dead-straight trail, where every
   valid position is equally straight) prefer the run centered closest to
   the path's own midpoint, so a straight trail's label still lands
   dead-center same as before this existed. */
function findStraightestWindow(d, targetLength) {
    var points = parsePathPoints(d);
    var n = points.length;

    var cumulative = [0];
    for (var i = 1; i < n; i++) {
        var dx = points[i][0] - points[i - 1][0];
        var dy = points[i][1] - points[i - 1][1];
        cumulative.push(cumulative[i - 1] + Math.sqrt(dx * dx + dy * dy));
    }
    var totalLength = cumulative[n - 1] || 0;
    var pathCenter = totalLength / 2;

    var bearings = [0];
    for (var j = 1; j < n; j++) {
        var bx = points[j][0] - points[j - 1][0];
        var by = points[j][1] - points[j - 1][1];
        bearings.push(Math.atan2(by, bx) * 180 / Math.PI);
    }
    var overallBearing = bearings.length > 1 ? bearings[bearings.length >> 1] : 0;

    // Too few points to have a meaningful bearing, or the label doesn't
    // fit anywhere with margin either way -- just use the whole path.
    if (n < 3 || totalLength <= targetLength) {
        return {points: points, length: totalLength, bearing: overallBearing};
    }

    var half = targetLength / 2;
    var EPS = 1e-6;
    var bestError = Infinity;
    var bestLo = 0, bestHi = n - 1;
    var bestBearing = overallBearing;
    var bestDistFromPathCenter = Infinity;

    for (var k = 0; k < n; k++) {
        var center = cumulative[k];
        if (center - half < 0 || center + half > totalLength) continue;

        var lo = k, hi = k;
        while (lo > 0 && cumulative[lo] > center - half) lo--;
        while (hi < n - 1 && cumulative[hi] < center + half) hi++;

        var sum = 0, count = 0;
        for (var m = lo + 1; m <= hi; m++) { sum += bearings[m]; count++; }
        if (count === 0) continue;
        var mean = sum / count;
        var error = 0;
        for (var p = lo + 1; p <= hi; p++) error += Math.abs(bearings[p] - mean);

        var distFromPathCenter = Math.abs(center - pathCenter);
        if (error < bestError - EPS ||
            (Math.abs(error - bestError) <= EPS && distFromPathCenter < bestDistFromPathCenter)) {
            bestError = error;
            bestLo = lo;
            bestHi = hi;
            bestBearing = mean;
            bestDistFromPathCenter = distFromPathCenter;
        }
    }
    return {
        points: points.slice(bestLo, bestHi + 1),
        length: cumulative[bestHi] - cumulative[bestLo],
        bearing: bestBearing,
    };
}

/* Normalizes an angle in degrees to (-180, 180]. */
function normalizeAngle(deg) {
    return ((deg + 180) % 360 + 360) % 360 - 180;
}


var PolylineTextPath = {

    onAdd: function (map) {
        __onAdd.call(this, map);
        this._textRedraw();
    },

    onRemove: function (map) {
        map = map || this._map;
        if (map && this._textNode && this._renderer._container)
            this._renderer._container.removeChild(this._textNode);
        if (map && this._windowPathNode && this._renderer._container)
            this._renderer._container.removeChild(this._windowPathNode);
        __onRemove.call(this, map);
    },

    bringToFront: function () {
        __bringToFront.call(this);
        this._textRedraw();
    },

    _updatePath: function () {
        __updatePath.call(this);
        this._textRedraw();
    },

    _textRedraw: function () {
        var text = this._text,
            options = this._textOptions;
        if (text) {
            /* _textRedraw fires on every _updatePath -- i.e. every zoom
               level, since Leaflet recomputes every path's pixel
               coordinates then, not just at whatever moment the caller
               last explicitly called setText -- so it's the natural place
               for zoom-dependent attributes (e.g. a font-size that grows
               with zoom) to be refreshed too, without the caller having to
               separately re-invoke setText itself on every zoom level (a
               second full pass on top of this one -- doing the same
               straightest-window/flip work twice per zoom for every
               labeled layer). options.refreshAttributes, when given, is
               called fresh each time and merged over the stored
               attributes, instead of blindly replaying whatever was true
               when setText was last called explicitly. */
            if (options && options.refreshAttributes) {
                options = L.Util.extend({}, options, {
                    attributes: L.Util.extend({}, options.attributes, options.refreshAttributes())
                });
            }
            this.setText(null).setText(text, options);
        }
    },

    setText: function (text, options) {
        this._text = text;
        this._textOptions = options;

        /* If not in SVG mode or Polyline not added to map yet return */
        /* setText will be called by onAdd, using value stored in this._text */
        if (!L.Browser.svg || typeof this._map === 'undefined') {
          return this;
        }

        var defaults = {
            repeat: false,
            fillColor: 'black',
            attributes: {},
            below: false,
        };
        options = L.Util.extend(defaults, options);

        /* If empty text, hide */
        if (!text) {
            if (this._textNode && this._textNode.parentNode) {
                this._renderer._container.removeChild(this._textNode);

                /* delete the node, so it will not be removed a 2nd time if the layer is later removed from the map */
                delete this._textNode;
            }
            if (this._windowPathNode && this._windowPathNode.parentNode) {
                this._renderer._container.removeChild(this._windowPathNode);
                delete this._windowPathNode;
            }
            return this;
        }

        text = text.replace(/ /g, '\u00A0');  // Non breakable spaces
        var id = 'pathdef-' + L.Util.stamp(this);
        var svg = this._renderer._container;
        this._path.setAttribute('id', id);
        var pathD = this._path.getAttribute('d');

        var rotateAngle = 0;
        if (options.orientation) {
            switch (options.orientation) {
                case 'flip':
                    rotateAngle = 180;
                    break;
                case 'perpendicular':
                    rotateAngle = 90;
                    break;
                default:
                    rotateAngle = options.orientation;
            }
        }

        /* orientation 0 or 180 (the only values this app ever sends) both
           just mean "this is a real line, consider whether it needs to
           flip to stay upright" -- treat them as a hint, not the answer.
           They're computed server-side from the trail's raw midpoint, but
           the label doesn't render there anymore (see findStraightestWindow
           above); a trail can easily have its midpoint on one side of the
           upright/upside-down threshold and its actual straightest,
           label-bearing window on the other, in EITHER direction (a "180"
           guess that turns out not to need flipping, or a "0" guess that
           does). Rather than trust either specific value, or rotate the
           finished, already-curved text (which mirrors the whole letter
           arrangement and makes it hug the trail's curve backwards), work
           out whether a flip is ACTUALLY needed at wherever the label will
           really be centered: that window's own bearing combined with the
           map's current rotation (leaflet-rotate's bearing, a CSS transform
           applied uniformly to the whole pane after this layout, so it adds
           directly to a local bearing angle here) tells us whether it'll
           read upside down to the viewer.

           A closed polygon ring (Leaflet's SVG renderer appends "z" to an
           area trail's outline) has no single meaningful direction, so it's
           left alone -- same as the old server-side check's is_area gate. */
        var isClosedRing = /z\s*$/i.test(pathD);
        var window_ = null;
        var flipped = false;
        if (options.center) {
            var measureNode = L.SVG.create('text');
            for (var mAttr in options.attributes)
                measureNode.setAttribute(mAttr, options.attributes[mAttr]);
            measureNode.appendChild(document.createTextNode(text));
            svg.appendChild(measureNode);
            var measuredLength = measureNode.getComputedTextLength();
            svg.removeChild(measureNode);

            window_ = findStraightestWindow(pathD, measuredLength);

            if (!isClosedRing && (!options.orientation || rotateAngle === 180)) {
                var mapBearing = (this._map.getBearing ? this._map.getBearing() : 0) || 0;
                flipped = Math.abs(normalizeAngle(window_.bearing + mapBearing)) > 90;
            }
        }

        /* Reference a small standalone path built from just the chosen
           window's points, instead of the full original path with an
           arc-length offset into it. Referencing deep into a long,
           many-segment path at a nonzero offset measurably confuses the
           browser's per-glyph rotation for textPath -- confirmed by
           rendering the identical points both ways: as their own short
           path starting at 0, they render right-side up; reached via an
           offset into the full original path, the same points render
           upside down. Building a dedicated window path (as was already
           done for the flipped case) sidesteps that entirely, for both
           the flipped and non-flipped case. */
        var hrefId = id;
        var hrefD = pathD;
        var windowLength = this._path.getTotalLength();
        if (window_) {
            hrefId = id + '-window';
            var windowPoints = flipped ? reversePoints(window_.points) : window_.points;
            hrefD = pointsToD(windowPoints);
            windowLength = window_.length;
            var windowPath = L.SVG.create('path');
            windowPath.setAttribute('id', hrefId);
            windowPath.setAttribute('d', hrefD);
            windowPath.setAttribute('style', 'display:none');
            svg.appendChild(windowPath);
            this._windowPathNode = windowPath;
        }

        if (options.repeat) {
            /* Compute single pattern length */
            var pattern = L.SVG.create('text');
            for (var attr in options.attributes)
                pattern.setAttribute(attr, options.attributes[attr]);
            pattern.appendChild(document.createTextNode(text));
            svg.appendChild(pattern);
            var alength = pattern.getComputedTextLength();
            svg.removeChild(pattern);

            /* Create string as long as path */
            text = new Array(Math.ceil(isNaN(this._path.getTotalLength() / alength) ? 0 : this._path.getTotalLength() / alength)).join(text);
        }

        /* Put it along the path using textPath */
        var textNode = L.SVG.create('text'),
            textPath = L.SVG.create('textPath');

        var dy = options.offset || this._path.getAttribute('stroke-width');
        /* Walking the path backwards flips which side of the line the offset
           lands on -- confirmed empirically (measuring rendered glyph
           position against the path) that negating dy here to try to
           compensate collapses the offset to ~0 instead of preserving it on
           the opposite side, so the label ends up sitting on the line with
           no readable gap. Leaving dy as-is keeps a full-magnitude offset,
           just mirrored to the other side of the trail for a flipped label. */

        textPath.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", '#'+hrefId);
        textNode.setAttribute('dy', dy);
        for (var attr in options.attributes)
            textNode.setAttribute(attr, options.attributes[attr]);
        textPath.appendChild(document.createTextNode(text));
        textNode.appendChild(textPath);
        this._textNode = textNode;

        if (options.below) {
            svg.insertBefore(textNode, svg.firstChild);
        }
        else {
            svg.appendChild(textNode);
        }

        /* Place the label centered within the window path referenced above
           (see findStraightestWindow) -- picked for being the straightest
           run of the original path long enough to fit the label, instead
           of always dead-centering on the whole path. */
        if (options.center) {
            var textLength = textNode.getComputedTextLength();
            textNode.setAttribute('dx', (windowLength / 2) - (textLength / 2));
        }

        /* Change label rotation (if required) -- a 180-degree orientation is
           always handled above via the window-based flip decision instead
           (whether or not it actually decided to flip), never here: this
           was applying a second, stray 180-degree rotation on top of an
           already-correct render whenever that decision came out false. */
        if (rotateAngle && rotateAngle !== 180) {
            var rotatecenterX = (textNode.getBBox().x + textNode.getBBox().width / 2);
            var rotatecenterY = (textNode.getBBox().y + textNode.getBBox().height / 2);
            textNode.setAttribute('transform','rotate(' + rotateAngle + ' '  + rotatecenterX + ' ' + rotatecenterY + ')');
        }

        /* Initialize mouse events for the additional nodes */
        if (this.options.interactive) {
            if (L.Browser.svg || !L.Browser.vml) {
                textPath.setAttribute('class', 'leaflet-interactive');
            }

            var events = ['click', 'dblclick', 'mousedown', 'mouseover',
                          'mouseout', 'mousemove', 'contextmenu'];
            for (var i = 0; i < events.length; i++) {
                L.DomEvent.on(textNode, events[i], this.fire, this);
            }
        }

        return this;
    }
};

L.Polyline.include(PolylineTextPath);

L.LayerGroup.include({
    setText: function(text, options) {
        for (var layer in this._layers) {
            if (typeof this._layers[layer].setText === 'function') {
                this._layers[layer].setText(text, options);
            }
        }
        return this;
    }
});



})();
