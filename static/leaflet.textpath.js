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
   (see pointsToPath in leaflet's SVG.Util.js) -- walk the same points in
   reverse to get a path that traces the identical curve from the other end.

   Points closer together than MIN_POINT_SPACING are dropped first (except
   the endpoints). SVG's textPath places each glyph as a rigid shape
   following the tangent at a single sampled point; a run of points closer
   together than a glyph is wide gives consecutive glyphs almost the same
   tangent-sample spacing as their own width, so they overlap. This is only
   visible walking the path backwards -- forward rendering of the same
   dense points (e.g. a catwalk with many closely-surveyed OSM nodes) is
   fine -- so it's corrected here rather than for every path. */
var MIN_POINT_SPACING = 15;
function reversePathD(d) {
    var nums = d.match(/-?\d+\.?\d*/g) || [];
    var points = [];
    for (var i = 0; i < nums.length; i += 2) {
        points.push([parseFloat(nums[i]), parseFloat(nums[i + 1])]);
    }
    var kept = [points[0]];
    for (var j = 1; j < points.length - 1; j++) {
        var last = kept[kept.length - 1];
        var dx = points[j][0] - last[0], dy = points[j][1] - last[1];
        if (Math.sqrt(dx * dx + dy * dy) >= MIN_POINT_SPACING) kept.push(points[j]);
    }
    kept.push(points[points.length - 1]);
    kept.reverse();
    return kept.map(function (p, i) { return (i ? 'L' : 'M') + p[0] + ' ' + p[1]; }).join('');
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
        if (map && this._reversedPathNode && this._renderer._container)
            this._renderer._container.removeChild(this._reversedPathNode);
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
            if (this._reversedPathNode && this._reversedPathNode.parentNode) {
                this._renderer._container.removeChild(this._reversedPathNode);
                delete this._reversedPathNode;
            }
            return this;
        }

        text = text.replace(/ /g, '\u00A0');  // Non breakable spaces
        var id = 'pathdef-' + L.Util.stamp(this);
        var svg = this._renderer._container;
        this._path.setAttribute('id', id);

        /* A 180-degree orientation means the path's natural direction would
           render the label upside down. Rather than rotate the finished,
           already-curved text (which mirrors the whole letter arrangement
           and makes it hug the trail's curve backwards), point textPath at
           a reversed-point copy of the same path so glyphs still follow the
           trail's true curve, just walked from the other end. */
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
        var flipped = rotateAngle === 180;
        var hrefId = id;
        if (flipped) {
            hrefId = id + '-reversed';
            var reversedPath = L.SVG.create('path');
            reversedPath.setAttribute('id', hrefId);
            reversedPath.setAttribute('d', reversePathD(this._path.getAttribute('d')));
            reversedPath.setAttribute('style', 'display:none');
            svg.appendChild(reversedPath);
            this._reversedPathNode = reversedPath;
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

        /* Center text according to the path's bounding box */
        if (options.center) {
            var textLength = textNode.getComputedTextLength();
            var pathLength = this._path.getTotalLength();
            /* Set the position for the left side of the textNode */
            textNode.setAttribute('dx', ((pathLength / 2) - (textLength / 2)));
        }

        /* Change label rotation (if required) -- the 180-degree case is
           already handled above by reversing the referenced path instead */
        if (rotateAngle && !flipped) {
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
