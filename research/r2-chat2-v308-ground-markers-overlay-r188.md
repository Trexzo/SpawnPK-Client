# Chat 2 — exact-v308 Ground Markers overlay R188

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R188 is a separate non-canonical class-only review for the live rendering overlay owned by
the reviewed Ground Markers plugin.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_95BC6E624B359474EB6B`
- field/method proposals: **0**

## Stable ID

`rs/s/f/c` -> `CLIENT_CLASS_000909` -> `GroundMarkerOverlay`

## Exact runtime role

The class extends the shared overlay base and stores only:

- reviewed `GroundMarkerConfig`;
- reviewed `GroundMarkerPlugin`.

Its render method requests the plugin's live `ColorTileMarker` collection, then for each
marker:

1. skips markers on a different plane;
2. resolves marker color, falling back to the configured default;
3. constructs the tile polygon from the marker WorldPoint;
4. draws configured border/fill using border width and fill opacity;
5. renders the optional marker label.

R19 already recovered `ColorTileMarker` and `GroundMarkerPoint`; R9 already recovered the
Ground Markers config/plugin pair. The remaining class therefore has one exact responsibility:
rendering those markers.

## Serialization-helper boundary

Adjacent `rs/s/f/e` is only a Gson `TypeToken<List<GroundMarkerPoint>>` captured by the
plugin persistence path.

R188 deliberately leaves that implementation helper unnamed rather than assigning semantics
to every anonymous generic token.

## Confidence boundary

`GroundMarkerOverlay` is **0.999**.

The name is descriptive exact-behavior recovery, not a claim about a lost original source
identifier.

## Acceptance boundary

R188 remains class-only and non-canonical. Main/Core may accept the proposal only through an
explicit `semantic_acceptance_spec` bound to `SEMREVIEW_95BC6E624B359474EB6B`.


## Source-identity correction after R242

Historical RuneLite source at `68c819924cfd6bfb4848c71f74c121109f289d5a` fixes the original class identity as singular `GroundMarkerOverlay`. The later attempted R241 rediscovery was therefore redundant and is removed; this R188 review is the authoritative non-canonical proposal for `CLIENT_CLASS_000909`.
