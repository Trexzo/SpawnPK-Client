# Chat 2 — exact-v308 overlay framework R213

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R213 is a separate non-canonical class-only review for the core overlay lifecycle,
registry, panel and renderer framework.

R12 already owns the exact self-labeled `OverlayBounds` and `OverlayMenuEntry`
value classes, and R160 already owns `OverlayPosition`. R213 does not duplicate those
owners. It closes the previously unnamed framework around them.

## Deterministic review result

- candidate classes: **5**
- resolved proposals: **5**
- unresolved: **0**
- review ID: `SEMREVIEW_60409C2E417ECC4CC51D`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a` -> `CLIENT_CLASS_000441` -> `OverlayRenderStage`
- `rs/l/f/b` -> `CLIENT_CLASS_000479` -> `Overlay`
- `rs/l/f/e` -> `CLIENT_CLASS_000486` -> `OverlayManager`
- `rs/l/f/g` -> `CLIENT_CLASS_000488` -> `OverlayPanel`
- `rs/l/f/i` -> `CLIENT_CLASS_000490` -> `OverlayRenderer`

All stable IDs were recomputed from the exact v308 sorted `rs/**.class`
seed-lineage ordering.

## OverlayRenderStage

The enum preserves 27 exact lifecycle constants, including:

- `ITEM_3D_PRE_SHADE`
- `PLAYER_3D_PRE_SHADE`
- `NPC_3D_PRE_SHADE`
- `OBJECT_3D_PRE_SHADE`
- `ANIMABLE_PRE_RENDER`
- `NPC_3D_STAGE`
- `PLAYER_3D_STAGE`
- `ENTITY_3D_STAGE`
- `NPC_2D_STAGE`
- `PLAYER_2D_STAGE`
- `ENTITY_2D_STAGE`
- `WORLD_BEFORE_ENTITIES`
- `AFTER_3D_BEFORE_2D`
- `AFTER_WORLD_BEFORE_WIDGETS`
- `AFTER_WIDGETS_BEFORE_INTERFACE`
- `AFTER_WIDGETS_BEFORE_INTERFACE_HIGH`
- `ON_INTERFACE_COMPONENT`
- `TAB_AREA`
- `AFTER_TAB_AREA_BEFORE_MENU`
- `AFTER_TAB_AREA_BEFORE_MENU_HIGH`
- `AFTER_ALL_PRIORITY_NONE/LOW/MID/HIGH`
- `CONTEXT_MENU`
- `OVERLAY`.

Overlay owns primary/secondary values of this enum. OverlayPanel owns an additional
preferred/override value. OverlayManager initializes collections for every value and uses
the enum as the exact dispatch key.

The role is therefore render-stage identity, not a feature/domain enum.

## Overlay

`rs/l/f/b` is the abstract common root for the overlay system.

Direct subclasses include:

- `OverlayPanel`;
- the actor/widget overlay bases under `rs/l/f/b/*`;
- the already-reviewed TooltipOverlay;
- the reviewed overlay-particle manager;
- reviewed raid progress/text/combat-style render components.

It owns:

- enabled state;
- primary and secondary OverlayRenderStage;
- the live Client binding;
- shared shape/text drawing helpers;
- world-to-screen projection helpers.

OverlayManager's non-panel registry is literally
`Map<OverlayRenderStage, List<rs/l/f/b>>`, and its public registration lifecycle is
defined on this exact type.

That closes the class as the overlay root rather than a generic rendering utility.

## OverlayManager

`rs/l/f/e` owns two stage-keyed registries:

- `List<Overlay>` for general overlays;
- `CopyOnWriteArrayList<OverlayPanel>` for positionable panels.

It implements exact:

- registration;
- unregistration;
- membership testing;
- per-stage rendering/dispatch;
- actor/widget-stage dispatch.

Its constructor creates and registers reviewed global overlay instances including:

- TooltipOverlay;
- OverlayParticleManager;
- several exact combat/text/global overlays;
- NPC/item/object recoloring overlays.

It also owns the single OverlayRenderer instance and exposes the static live manager
instance through `d()`.

## OverlayPanel

`rs/l/f/g` extends Overlay and owns one `rs/ui/components/s` component tree.

The component tree carries:

- bounds;
- preferred dimension;
- color;
- child components.

OverlayPanel adds:

- current and override OverlayPosition;
- rendered bounds;
- explicit point/dimension state;
- priority;
- preferred render stage;
- visibility/interactivity flags.

It is the direct base of reviewed classes including:

- ConfigurableActionPromptOverlay;
- BossBarOverlay;
- BountyHunterOverlay;
- raid panel overlays.

OverlayManager keeps OverlayPanel objects in their own stage-keyed list and routes those
lists through OverlayRenderer.

## OverlayRenderer

`rs/l/f/i` is constructed exactly once by OverlayManager.

For each stage it receives:

`(OverlayRenderStage, List<OverlayPanel>)`

and performs the panel rendering pipeline.

It resolves effective OverlayPosition values, consumes R12 OverlayBounds, computes anchored
and stacked points, clips the stage Graphics2D and renders each panel.

It also owns the mouse/focus interaction path:

- press;
- drag;
- release;
- move;
- focus changes.

Those paths manage detached/dynamic/fixed placement, drag-target rectangles and persisted
preferred positions. R160 independently identified this class as the central renderer
consumer of OverlayPosition.

## Already-owned supporting infrastructure

R213 deliberately does not duplicate:

- R12 `rs/l/f/c` / `CLIENT_CLASS_000484` -> `OverlayBounds`;
- R12 `rs/l/f/f` / `CLIENT_CLASS_000487` -> `OverlayMenuEntry`;
- R160 `rs/l/f/l` / `CLIENT_CLASS_000493` -> `OverlayPosition`.

The exact v308 class files retain the self-label strings
`OverlayBounds(...)` and `OverlayMenuEntry(...)`, which independently anchor the
surrounding framework noun.

## Naming boundary

All five R213 names are descriptive exact-behavior recovery at confidence **0.999**.

They do not claim surviving original Java identifiers. The names are constrained by exact
enum literals, exact hierarchy/registry types, manager dispatch, component-panel behavior,
renderer geometry and the already-reviewed OverlayBounds/OverlayPosition infrastructure.

R213 adds no field or method proposals.

## Acceptance boundary

Chat 2 does not promote R213. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_60409C2E417ECC4CC51D`.
