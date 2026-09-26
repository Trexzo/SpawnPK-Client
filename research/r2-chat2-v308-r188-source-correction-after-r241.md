# Chat 2 — R188 GroundMarkerOverlay source correction after R241

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R188 had already reviewed `rs/s/f/c` / `CLIENT_CLASS_000909` under the descriptive label `GroundMarkersOverlay`.

A later historical-source audit during R241 found RuneLite `GroundMarkerOverlay` at `68c819924cfd6bfb4848c71f74c121109f289d5a`, matching exact v308 nearly statement-for-statement: `MAX_DRAW_DISTANCE = 32`, Ground Markers config/plugin pairing, ColorTileMarker iteration, plane filtering, marker-color fallback, configurable border/fill rendering, and optional label drawing.

Therefore:

- R188 is corrected to `GroundMarkerOverlay`
- corrected R188 review: `SEMREVIEW_95BC6E624B359474EB6B`
- the attempted R241 batch is redundant and removed rather than retained as a duplicate proposal

Proposal count does not increase from this correction. No semantic acceptance is performed.
