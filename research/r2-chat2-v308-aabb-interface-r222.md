# Chat 2 — exact-v308 RuneLite AABB interface correction R222

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R222 performs one source-proven class review together with the required R32 correction.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_3EDCD5721A8A23544C73`
- field/method proposals: **0**

## Stable ID

- `rs/runelite/a/a` -> `CLIENT_CLASS_000809` -> `AABB`

## Exact interface

The exact v308 class is an interface containing precisely six integer getters. Its concrete
implementation `rs/a/i` stores the six model-bound values produced by Model: three centers
and three half-extents.

RuneLite commit `5dffa0133efcf32e5e0c7e488dbf24ef5f781630` introduced
`net.runelite.api.AABB` with precisely:

- `getCenterX()`;
- `getCenterY()`;
- `getCenterZ()`;
- `getExtremeX()`;
- `getExtremeY()`;
- `getExtremeZ()`.

That is an exact source-name provenance match for the surviving v308 API interface.

## Required R32 correction

R32 originally proposed `AABB` for `rs/a/i`. That was a conservative behavioral name
before the API interface was source-resolved.

R222 atomically corrects R32:

- `rs/a/i` / `CLIENT_CLASS_000072`: `AABB` -> `ModelAABB`;
- old R32 proposal `SEMPROP_0B9E8DFA9594EE5A8031` is superseded by `SEMPROP_E4204F44044713ABAD56`;
- old R32 review `SEMREVIEW_F5DD2732F728A2946B02` is superseded by `SEMREVIEW_FC24DE0B8A0F2CAF799C`.

No proposal count changes. The correction removes the name collision while assigning the
upstream-proven source noun to the interface that actually carried it.

## Acceptance boundary

Chat 2 does not promote R222 or corrected R32. Main/Core may accept only through explicit
semantic acceptance bound to the corresponding corrected review IDs.
