# Chat 2 — exact-v308 Player Outline overlays R187

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R187 is a separate non-canonical class-only review for the two live overlays owned by the
reviewed Player Outline plugin.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_75AAAF2DB6589C9AAFAB`
- field/method proposals: **0**

## Stable IDs

- `rs/s/p/b` -> `CLIENT_CLASS_000947` -> `PlayerOutlineOverlay`
- `rs/s/p/c` -> `CLIENT_CLASS_000948` -> `PetOutlineOverlay`

## PlayerOutlineOverlay

Reviewed `PlayerOutlinePlugin` registers `rs/s/p/b` unconditionally during startup.

The overlay render path targets `Client.eR`, whose type `rs/a/k` was independently
recovered in R30 as `Player`.

It obtains that player's model and invokes the shared outline renderer using the reviewed
`PlayerOutlineConfig` values for:

- outline color;
- feather;
- border width.

The class has no unrelated rendering responsibility.

That fixes `rs/s/p/b` as the always-active local-player outline overlay.

## PetOutlineOverlay

The second sibling overlay `rs/s/p/c` is optional.

Reviewed `PlayerOutlinePlugin` adds or removes it solely through the exact configuration
key:

`petOutline`

including the plugin's `ConfigChanged` path.

The overlay targets `rs/a/j`, independently recovered in R30 as `Npc`, and inspects the
bound `NpcDefinition` before rendering the same configured outline style.

The pair is therefore asymmetric and exact:

- `PlayerOutlineOverlay`: always registered, local Player target;
- `PetOutlineOverlay`: config-gated by `petOutline`, Npc/pet target.

## Naming boundary

Both names are descriptive exact-behavior recovery at **0.999**.

They do not claim lost developer identifiers. The identities are fixed by the reviewed plugin
lifecycle, exact config key and independently reviewed target actor types.

## Acceptance boundary

R187 remains class-only and non-canonical. Main/Core may accept either proposal only through
an explicit `semantic_acceptance_spec` bound to `SEMREVIEW_75AAAF2DB6589C9AAFAB`.
