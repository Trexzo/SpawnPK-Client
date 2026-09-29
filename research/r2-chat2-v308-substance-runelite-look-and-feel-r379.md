# Chat 2 — SubstanceRuneLiteLookAndFeel source recovery R379

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/a` -> `CLIENT_CLASS_000202` -> `SubstanceRuneLiteLookAndFeel`
- proposal: `SEMPROP_89EB5E6531A88D8B83B4`
- review: `SEMREVIEW_9A690D5111C98C746A99`

## Exact structure

The class:

- extends `org.pushingpixels.substance.api.SubstanceLookAndFeel`;
- has no fields and no extra methods;
- constructs the already-owned R22 `rs/gui/b` `RuneLiteSkin`;
- passes that skin directly to the superclass constructor.

## Source match

Historical RuneLite/OpenOSRS exposes:

`net.runelite.client.ui.skin.SubstanceRuneLiteLookAndFeel`

with the same SubstanceLookAndFeel base and RuneLiteSkin constructor relationship.

That is strong enough for exact source-name recovery rather than a descriptive alias.

R379 remains non-canonical Chat 2 semantic research only.
