# Chat 2 — exact-v308 Trading Post listing image loader R195

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R195 is a separate non-canonical class-only review for the bounded image loader used by the
reviewed Trading Post listing panel.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_948493F4C27B142BD65D`
- field/method proposals: **0**

## Stable ID

`rs/s/t/f` -> `CLIENT_CLASS_000968` -> `TradingPostListingImageLoader`

## Existing Trading Post authority

The surrounding feature is already reviewed, including:

- `TradingPostPlugin`;
- `TradingPostListing`;
- `TradingPostListingPanel`;
- `TradingPostListingsPanel`.

R195 therefore names only the remaining helper's exact role.

## Exact construction point

`TradingPostListingPanel` first asks `TradingPostPlugin` for the image associated with the
current listing's item id.

If an image already exists, the panel installs it directly.

Only when that lookup returns null does it construct `rs/s/t/f`, passing:

- the current `TradingPostListingPanel`;
- the current `TradingPostListing`.

The helper is scheduled through the client's loop-task machinery.

## Exact loading loop

The helper stores only:

- an attempt counter;
- the reviewed listing;
- the reviewed listing panel.

Its `loop()` behavior is narrow:

1. do nothing until the client is in the loaded state;
2. increment the attempt count;
3. stop once three attempts have been reached;
4. request the image from `TradingPostPlugin` using the listing's item id;
5. return true when the image is still unavailable so the scheduler can retry;
6. when the image resolves, schedule one Swing callback and terminate.

## Exact UI sink

The Swing callback updates exactly one component:

the item-image JLabel owned by `TradingPostListingPanel`.

It wraps the resolved Image in an ImageIcon and installs it on that label.

There is no search, pricing, packet decoding, generic cache management or unrelated UI
responsibility in the helper.

## Naming boundary

`TradingPostListingImageLoader` is **0.999**.

The name describes the externally meaningful responsibility rather than the generic loop-task
mechanism used to schedule it. It is not claimed as a surviving original source identifier.

R195 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R195. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_948493F4C27B142BD65D`.
