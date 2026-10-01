# Chat 2 — exact-v308 shop-tabs interface patch R451

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aO` -> `CLIENT_CLASS_000590` -> `ShopTabsInterfacePatch`
- proposal: `SEMPROP_4D0B143F1D307EC177B5`
- review: `SEMREVIEW_AFE23BD9019C48358A9B`

## Exact behavior

The class patches existing shop root widget **3824**.

It:

- scans existing children and removes text containing `Right-click on shop`;
- moves existing stock widget **3900** down by 23 pixels;
- extends the root by ten children;
- adds five clickable tab buttons;
- assigns exact tooltip `Select shop tab`;
- adds exact labels `Tab 1` through `Tab 5`;
- uses exact `slayer/image` assets.

## Naming boundary

Although the assets are in the slayer resource family, the code patches the shared shop
root and the labels remain generic. R451 therefore stops at `ShopTabsInterfacePatch`
instead of claiming a complete Slayer-shop screen identity.

R451 remains non-canonical Chat 2 semantic research only.
