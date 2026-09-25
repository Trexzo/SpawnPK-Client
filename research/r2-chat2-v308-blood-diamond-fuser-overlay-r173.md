# Chat 2 — exact-v308 Blood Diamond Fuser runtime presentation R173

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R173 is a separate non-canonical class-only review for the untouched runtime item-slot
presentation layered over the already-reviewed Blood Diamond Fuser interface.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_363CA780B1D65911DBB4`
- field/method proposals: **0**

## Stable IDs

- `rs/l/c/a` -> `CLIENT_CLASS_000384` -> `BloodDiamondFuserOverlay`
- `rs/l/c/c` -> `CLIENT_CLASS_000386` -> `BloodDiamondFuserItemEntry`

## Existing interface authority

R5 already resolves `rs/n/c/j` as `BloodDiamondFuserInterface`.

Its exact v308 title is:

`Blood Diamond Fuser`

and its surviving explanatory text says:

`Fuse items to sacrifice them into blood diamonds!`

R173 recovers the separate runtime classes responsible for drawing packet-populated item
slots over that interface.

## BloodDiamondFuserOverlay

Client constructs one `rs/l/c/a` instance during startup and stores it in the live Client.

The main rendering path invokes the overlay every frame.

Its render method exits unless the exact Blood Diamond Fuser interface is active:

`Client.cH == rs/n/c/j.c`

so the class has no second interface responsibility.

The overlay owns exactly three runtime entries and exactly three two-point slot geometries.

For every populated entry it:

- resolves the entry item id through the item-definition path;
- lazily builds/caches the item sprite;
- draws the sprite at the corresponding fuser slot;
- renders one numeric item value beside the item;
- renders the second numeric value against the shared fuser presentation sprite.

The positioning code applies the same fixed/resizable interface offsets used by the other
exact `rs/l/c` runtime overlays.

## Exact packet population

A live Client decode path handles selector/value **13** by splitting a String on commas.

It requires exactly **four integers** and passes them directly to:

`BloodDiamondFuserOverlay.a(int,int,int,int)`

The first integer selects one of the three overlay slots.

The remaining three values construct that slot's `BloodDiamondFuserItemEntry`.

This is independent packet-to-runtime evidence tying the overlay to live interface state,
not merely a static UI helper.

## BloodDiamondFuserItemEntry

`rs/l/c/c` is a compact runtime record containing:

- one cached item sprite;
- one item-id integer;
- two further numeric display values.

The overlay's exact usage proves the item-id role because it passes that getter into the item
definition/sprite loader.

The other two integers are both rendered numerically by the fuser overlay. R173 deliberately
does not invent narrower semantic names for those subfields because the exact client does not
yet prove whether each is quantity, cost, yield or another fuser-specific value.

The class-level role as one Blood Diamond Fuser item entry is nevertheless exact.

## Naming boundary

`BloodDiamondFuserOverlay` is **0.999** because:

- the target interface already has reviewed identity;
- the renderer has an exclusive interface-root guard;
- Client owns and renders it live;
- packet selector 13 populates it directly;
- it has exactly the fuser's three item slots.

`BloodDiamondFuserItemEntry` is **0.997** because its item identity and owning subsystem are
exact, while the two numeric subfield meanings intentionally remain unresolved.

Neither name is claimed as a stripped original developer identifier.

R173 remains class-only.

## Acceptance boundary

Chat 2 does not promote R173. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_363CA780B1D65911DBB4`.
