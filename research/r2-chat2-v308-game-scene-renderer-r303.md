# Chat 2 — exact-v308 game scene renderer R303

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/l/b/c` -> `CLIENT_CLASS_000381` -> `GameSceneRenderer`
- review: `SEMREVIEW_C13F4E48CFAAB9CB2FA6`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

The class is the live logged-in world-scene render phase.

- The main render coordinator `rs/l/b/a` calls `rs/l/b/c.a(Client)` for the active game scene.
- It derives the live camera pitch, yaw and position from Client/player state.
- It applies the client's five camera-shake channels before world projection/rendering and restores camera state afterward.
- R133 independently established that this exact class consumes `Client.aa` / `ScenePolygonManager`, projects its polygon records into the live scene and renders their fill/outline presentation.
- After scene/world-overlay work it hands off to `rs/l/b/b` for broader HUD/gameframe presentation and then the remaining post-scene client hooks.

That separates the responsibility cleanly from R302 `InterfaceRenderer`: R303 owns the world scene/camera render phase, while R302 owns recursive `rs/n/e` widget rendering.

## Deliberate exclusions

`rs/l/b/a` and `rs/l/b/b` remain unnamed here. Their exact responsibilities are broader render coordination/HUD composition and still deserve separate evidence rather than being named by adjacency.

## Boundary

R303 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
