# leaflet.heightgraph 1.4.0 (patched for feet)

Vendored copy of the `dist/` build of
[leaflet.heightgraph](https://github.com/GIScience/Leaflet.Heightgraph) 1.4.0
(MIT, see `LICENSE`), checked in rather than installed from npm because the
library hardcodes metric labels and has no units option.

`L.Control.Heightgraph.min.js` is hand-edited from the published build:

- Elevation labels (y-axis ticks, hover box, drag label) say `ft` instead of
  `m`. The values themselves aren't converted -- the profile data from
  `core.support.utils.build_elevation_profile` is already in feet.
- Distances (x-axis ticks, hover box distance and segment length) are
  converted from km to feet (`* 3281`, rounded) and labelled `ft`.
- Axis tick font size is `.8rem` instead of `10`.

The CSS and images are unmodified. To upgrade, reapply these edits to the new
version's `dist/L.Control.Heightgraph.min.js` (search for `" m"` and `" km"`).
