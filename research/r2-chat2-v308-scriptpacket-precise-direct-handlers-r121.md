# Chat 2 — exact-v308 remaining precise ScriptPacket handlers R121

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R121 is a separate non-canonical class-only review for three remaining direct R115
ScriptPacket handlers whose target state is now exact enough to name without guessing
unrecovered field semantics.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_5F55594AE7672CBEDED6`
- field/method proposals: **0**
- confidence: **0.998** each

## Stable IDs / ScriptPacket IDs

- `rs/q/a/a/a/n` -> `CLIENT_CLASS_000759`
  -> `InterfaceScrollPacketHandler` — ScriptPacket **5**
- `rs/q/a/a/a/f` -> `CLIENT_CLASS_000751`
  -> `InventorySlotOverlayPacketHandler` — ScriptPacket **37**
- `rs/q/a/a/a/g` -> `CLIENT_CLASS_000752`
  -> `ItemNumericOverlayPacketHandler` — ScriptPacket **39**

## ScriptPacket 5 — InterfaceScrollPacketHandler

The handler reads:

1. selector;
2. interface id;
3. integer value.

It resolves the interface from R56 `RSInterface.H`.

Selector 1 writes `RSInterface.V`.
Selector 2 writes `RSInterface.aH`.

The normal UI renderer independently fixes those field roles:

- `V` is clamped to the range from zero through `aH - aR`;
- `V` is passed as the vertical child-render offset;
- mouse/scrollbar input mutates `V`;
- the scrollbar is drawn when `aH > aR`.

Therefore the packet's complete responsibility is interface scrolling state, with `V` as
the current scroll position and `aH` as scroll maximum/content height.

## ScriptPacket 37 — InventorySlotOverlayPacketHandler

The handler resolves one R56 `RSInterface` and applies five modes.

The central state is `RSInterface.ay`, a String array.

R56 itself has an exact helper that allocates:

`ay = new String[az.length]`

where `az` is the widget's inventory item-id array.

Packet operations can:

- clear every slot String;
- set one slot String by index;
- fill every slot with one String;
- allocate/remove the slot String array;
- update the paired `ac/ap` inventory-grid layout values.

The live inventory renderer independently consumes:

`ay[slot]`

and draws that String directly over the corresponding rendered inventory item.

This fixes the role as per-inventory-slot overlay text rather than generic widget actions.

## ScriptPacket 39 — ItemNumericOverlayPacketHandler

The class owns one static Trove int-to-int map.

Its packet payload is:

- item id;
- integer overlay value.

Value `-2` removes the item id from the map. Other values insert/replace the mapping.

The live inventory renderer independently does:

1. derive `itemId = RSInterface.az[slot] - 1`;
2. check this exact map for the item id;
3. fetch the mapped integer;
4. render it as white text over the inventory slot.

A mapped value of `-1` renders literally as:

`?`

Other values render with `String.valueOf(int)`.

R121 deliberately stops at the exact role `ItemNumericOverlayPacketHandler`: v308 does
not prove whether the number means charges, value, count, durability or another
server-defined quantity.

## Deliberate exclusions

Two direct handlers remain outside R121.

### ScriptPacket 14 — `rs/q/a/a/a/h`

This is a large 26-mode mutator centered on another UI subsystem. Its operations are exact,
but the enclosing subsystem itself still lacks a strong enough recovered class identity to
give the packet handler one honest domain noun.

### ScriptPacket 32 — `rs/q/a/a/a/a`

This packet mixes several distinct Client-state operations. One selector unmistakably
switches Blood/Infernal spell widget names/sprites, but other selectors mutate unrelated
Client fields and toggles. Naming the entire class after only the spell-switch branch would
be misleading.

Both stay unnamed until a common subsystem identity is proven.

## Acceptance boundary

Chat 2 does not promote R121. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_5F55594AE7672CBEDED6`.
