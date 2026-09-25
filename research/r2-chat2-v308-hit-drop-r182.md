# Chat 2 — exact-v308 hit-drop presentation R182

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R182 is a separate non-canonical class-only review for the exact hit-drop record and manager
used by the client renderer.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_73905BBB0E66D66FB778`
- field/method proposals: **0**

## Stable IDs

- `rs/l/e/g` -> `CLIENT_CLASS_000428` -> `HitDropEntry`
- `rs/l/e/h` -> `CLIENT_CLASS_000429` -> `HitDropManager`

## Exact hit-drop vocabulary

The implementation itself loads:

- `popups/hit drop`;
- `popups/block drop`;
- `popups/drop bar`;
- `popups/protmelee`;
- `popups/protrange`;
- `popups/protmagic`.

R182 follows that surviving client vocabulary rather than importing a different hitsplat
terminology.

## HitDropEntry

One entry stores:

- numeric drop value/type state;
- x/y presentation position;
- alpha/fade state;
- optional protection-icon selector;
- timestamp;
- hit/block sprite.

The constructor selects the exact block-drop sprite for zero/block state and hit-drop sprite
otherwise.

Its update method performs the complete per-entry vertical/fade animation.

## HitDropManager

The manager owns:

- active entries;
- queued entries;
- removal staging;
- the exact drop-bar sprite.

On a new hit it creates a `HitDropEntry` at the fixed drop location.

Hits arriving within **100 ms** can aggregate into the most recent active entry; the resulting
entry selects exact block-drop vs hit-drop presentation based on the combined value.

If the active entries have not moved far enough vertically, new drops are queued. The manager
caps that queue and promotes the oldest queued entry when spacing permits.

The update/render pass:

1. advances active entry animation;
2. renders the drop-bar sprite;
3. renders hit/block presentation;
4. renders the selected melee/range/magic protection icon when present;
5. renders the numeric drop text;
6. stages and removes expired/faded entries;
7. promotes queued entries as room becomes available.

This is a complete whole-family role.

## Naming boundary

No matching public source identifier was found.

`HitDropEntry` (**0.998**) and `HitDropManager` (**0.999**) are descriptive names grounded
in the exact client asset vocabulary and complete behavior.

R182 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R182. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_73905BBB0E66D66FB778`.
