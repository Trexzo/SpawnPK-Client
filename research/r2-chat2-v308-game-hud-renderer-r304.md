# Chat 2 — exact-v308 game HUD renderer R304

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/l/b/b` -> `CLIENT_CLASS_000380` -> `GameHudRenderer`
- review: `SEMREVIEW_F6DDF6F3346CDA5899A9`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

R303 `GameSceneRenderer` invokes this class after the world-scene/camera phase.

The class then composes the visible game HUD/gameframe:

- positions and renders active `rs/n/e` roots through `Client.a(int,int,rs/n/e,int)`, which R302 proved delegates to `InterfaceRenderer`;
- renders exact runtime/debug HUD text including **RUNTIME INFORMATION**, **COORDINATE INFORMATION**, FPS, memory, ping, mouse coordinates, region id and interface/item diagnostics;
- owns live system-update warning/countdown presentation, including the launcher notification when the timer completes;
- renders tournament/lobby status such as **Waiting for more players** and **Tournament starts in:**;
- advances transient presentation managers including hit-drop/pop-up state and the scrolling/sliding text manager before returning to the scene phase.

That separates it from R303 `GameSceneRenderer` and R302 `InterfaceRenderer`: R304 is the post-scene HUD/gameframe composition layer.

## Deliberate exclusion

`rs/l/b/a` remains unnamed. It coordinates wider render/game-state transitions and still spans more than one narrowly provable presentation role.

## Boundary

R304 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
