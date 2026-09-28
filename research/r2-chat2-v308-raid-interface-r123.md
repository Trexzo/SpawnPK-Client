# Chat 2 — exact-v308 raid interface ScriptPacket 41 R123

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R123 is a separate non-canonical class-only review for the direct ScriptPacket handler
whose complete meaningful selector surface is confined to the exact raid interface and
raid-overlay subsystem.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_9352C6F0A9D8EE075D3C`
- field/method proposals: **0**

## Stable ID

`rs/n/c/d/d` -> `CLIENT_CLASS_000654` -> `RaidInterfacePacketHandler`

R115 registers this class directly as ScriptPacket **41**.

## Complete selector surface

The handler reads one selector integer.

Selectors **0–7** stay inside the `rs/n/c/d` raid UI subsystem:

- selector 0 updates `rs/n/c/d/a`;
- selectors 1–3 update `rs/n/c/d/c`;
- selectors 4–5 update `rs/n/c/d/b`;
- selector 6 updates `rs/n/c/d/f`;
- selector 7 toggles two exact interface widgets.

Selectors **8–14** have no branch.

Selectors **15–22** remain raid-specific:

- 15 enables/disables sibling raid overlays through the live overlay manager;
- 16 is a no-op;
- 17 updates one raid overlay's packet state;
- 18 enables/disables and initializes the raid party overlay timer;
- 19 updates raid party points;
- 20 updates the raid party elapsed/remaining time display;
- 21 toggles state in `rs/n/c/d/a` and refreshes the same raid interface;
- 22 updates the raid-difficulty requirement dropdown at interface **32430**.

No meaningful selector mutates an unrelated Client subsystem.

## Independent raid-interface evidence

The targeted `rs/n/c/d` classes preserve explicit raid vocabulary and assets.

`rs/n/c/d/a` includes:

- `Invocations`;
- `Party`;
- `raids/bg`;
- `raids/owner`;
- `raids/sprite 1` through `raids/sprite 4`;
- raid tab active/disabled/inactive assets.

`rs/n/c/d/b` includes:

- `Join party`;
- `Party<tab=150>Size<tab=225>Raid Type & Difficulty`;
- `Refresh party list`;
- `raids/list`.

`rs/n/c/d/c` includes:

- `Chambers of Xeric`;
- `Theatre of Blood`;
- `Raid Difficulty`;
- `Raid Selection`;
- `Party Afflictions`;
- `Enter Raid`;
- Adept, Expert, Master and Grandmaster difficulty descriptions;
- the `raids/*` resource family.

`rs/n/c/d/f` uses `raids/affbar2`.

This independently fixes the handler target as raid interface state rather than a generic
widget protocol.

## Independent raid-overlay evidence

The handler constructs `rs/l/f/a/g/a`.

That class preserves the exact literal:

`RaidPartyOverlay`

and renders exact labels:

- `Your points:`;
- `Time:`;
- default timer `0:00`.

Selectors 18–20 directly control that live overlay's visibility, timer and points.

The handler also constructs the sibling overlay `rs/l/f/a/g/c`, which preserves the exact
literal:

`RaidTheatreBar`

The remaining sibling overlay is managed by the same ScriptPacket modes and live overlay
manager.

## Raid difficulty requirement update

Selector 22 defaults the requirement suffix to:

`raids`

and updates the raid difficulty dropdown using surviving templates for:

- `Adept (Req. 10+ ...)`;
- `Expert (Req. 50+ ...)`;
- `Master (Req. 100+ ...)`.

This is another independent link from ScriptPacket 41 to the raid setup/interface domain.

## Naming boundary

`RaidInterfacePacketHandler` is descriptive at **0.998**.

The exact ScriptPacket ID, complete selector surface, target package vocabulary, raid
resource family and independent `RaidPartyOverlay`/`RaidTheatreBar` identities all agree.
The English class name is not claimed as a surviving original SpawnPK identifier.

R123 remains class-only.

## Deliberate exclusion remains

ScriptPacket 32 (`rs/q/a/a/a/a`) remains unnamed. R123 does not weaken the earlier
whole-class coherence rule.

## Acceptance boundary

Chat 2 does not promote R123. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_9352C6F0A9D8EE075D3C`.
