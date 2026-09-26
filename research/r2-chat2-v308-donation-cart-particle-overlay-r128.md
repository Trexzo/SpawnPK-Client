# Chat 2 — exact-v308 Donation Shopping Cart particle overlay R128

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R128 closes the ScriptPacket 36 research gap left deliberately open by R127. The exact
authority bridge is now explicit: the Donation Shopping Cart interface builder itself owns,
constructs and registers the packet-controlled particle overlay.

R128 remains a separate non-canonical class-only review.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_C9EEEC5E0D22C36FFC69`
- field/method proposals: **0**
- confidence: **0.998** each

## Stable IDs

- `rs/n/c/ax` -> `CLIENT_CLASS_000628`
  -> `DonationShoppingCartParticleOverlayPacketHandler`
- `rs/n/c/ay` -> `CLIENT_CLASS_000629`
  -> `DonationShoppingCartParticleOverlay`
- `rs/n/c/ay$a` -> `CLIENT_CLASS_000630`
  -> `DonationShoppingCartParticleStyle`

## Exact cart ownership

`rs/n/c/aw` builds the exact interface rooted at 60200 and preserves:

- `@or1@Donation Shopping Cart`;
- `Shopping Cart`;
- `Purchase Options`;
- `Checkout`;
- PayPal/Card/Bank and OSRS-GP choices;
- subtotal/offer text;
- `misc/cart` and `misc/donor` resources.

During that same builder's static initialization it constructs exactly one:

`new rs/n/c/ay()`

and stores it in private static field `cj`.

While laying out the cart widget tree, the builder:

1. places widget **60065**;
2. registers `cj` with the live overlay manager;
3. binds the same `cj` overlay instance specifically to widget **60065**.

This is the missing authority bridge that R127 intentionally did not assume.

## DonationShoppingCartParticleOverlay

`rs/n/c/ay` extends the client overlay base.

Its live draw/update path is cart-bound:

- it reads cart widgets **60249** and **60251**;
- it uses packet-controlled static integers `j` and `k` to draw progress/state bars;
- it stores a three-slot array of `rs/n/c/ay$a` values;
- each active style entry supplies parameters to repeated particle emission;
- emitted `rs/l/f/a/f/a` instances are passed into the live overlay particle manager.

The overlay is therefore not merely adjacent to the cart package: exact v308 shows the
Donation Shopping Cart builder constructs, registers and widget-binds that specific instance.

## Particle style enum

`rs/n/c/ay$a` is an enum with exact surviving constants:

- `GOLD_SLOW`;
- `PURPLE_EXOTIC`.

Each enum value stores five integers used directly by the overlay's particle-emission path.

The exact constants include:

- GOLD_SLOW: fixed geometry/emission parameters with packed gold color **16774912**;
- PURPLE_EXOTIC: a larger emission count plus packed colors **16711935** and **9765119**.

`DonationShoppingCartParticleStyle` is therefore descriptive but directly grounded in
surviving enum names and exact particle consumption.

## ScriptPacket 36

R115 registers ScriptPacket **36** from `rs/n/c/aw.d`.

The exact `rs/n/c/aw` static initializer assigns:

`new rs/n/c/ax()`

to that handler field.

The complete `rs/n/c/ax` selector surface is:

- selector 0: reset `rs/n/c/ay.j` and `rs/n/c/ay.k` to zero;
- selector 1: read a channel selector plus integer value, clamp the value to **0..457**,
  then write either `j` or `k`;
- selector 2: read a style-slot index and encoded enum index; `-1` clears the slot,
  otherwise the matching `rs/n/c/ay$a.values()` entry is installed.

No branch mutates any second subsystem.

R128 deliberately does not invent narrower names for `j` or `k`; only their exact
packet-controlled progress/state behavior is asserted.

## Naming boundary

None of the three English class names is claimed as an original developer identifier.

The domain chain is exact:

Donation Shopping Cart builder
-> builder-owned widget-bound overlay
-> exact GOLD_SLOW/PURPLE_EXOTIC particle styles
-> ScriptPacket 36 handler controlling only that overlay.

Confidence is **0.998** rather than 0.999 because the broader cart/particle roles are exact
while some individual overlay-state field nouns remain unknown.

## Acceptance boundary

Chat 2 does not promote R128. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_C9EEEC5E0D22C36FFC69`.
