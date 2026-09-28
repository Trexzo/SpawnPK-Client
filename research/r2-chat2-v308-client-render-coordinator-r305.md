# Chat 2 — exact-v308 client render coordinator R305

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/l/b/a` -> `CLIENT_CLASS_000367` -> `ClientRenderCoordinator`
- review: `SEMREVIEW_1BFE70D3146AA85EA457`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

R302-R304 split the concrete rendering responsibilities:

- R302 `InterfaceRenderer` recursively renders `rs/n/e` widgets;
- R303 `GameSceneRenderer` owns camera/world-scene rendering;
- R304 `GameHudRenderer` owns post-scene HUD/gameframe composition.

`rs/l/b/a` sits above all of those layers.

Its top-level `a(Client)` render pass:

- detects client-size changes and rebuilds the `rs/l/C` frame/back buffer plus layout/projection state;
- handles the exact **Loading, please wait..** presentation path;
- posts RuneLite `GameStateChanged` while coordinating the transition into active rendering;
- performs broad interface/root invalidation and redraw bookkeeping;
- dispatches to R303 `GameSceneRenderer` for logged-in scene rendering or the alternate Client presentation path for other states;
- composes fixed-frame resources `gameframe/backleft1` and `gameframe/backtop1` when applicable;
- blits the completed frame buffer to the live client `Graphics` target and runs post-frame hooks.

This is broader than one visual renderer. `ClientRenderCoordinator` therefore describes the proven orchestration boundary without claiming a surviving original source noun.

## Boundary

R305 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
