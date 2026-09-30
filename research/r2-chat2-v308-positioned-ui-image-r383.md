# Chat 2 — R383 duplicate owner audit

Exact client authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R383 retains **no semantic proposal**.

The attempted `rs/gui/x -> CLIENT_CLASS_000285 -> PositionedUiImage` proposal duplicates the exact owner already reviewed in R345 as `GuiImageAsset`.

Direct bytecode still corroborates the R345 owner: it loads a UI image resource, retains mutable x/y coordinates and draws the image at that position for launcher/loadout presentation consumers. That evidence does not justify a second semantic identity.

The R383 candidate/review/test are removed. R383 performs no semantic acceptance or rewrite.
