# Chat 2 — exact-v308 Trading Post listing model R194

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R194 is a separate non-canonical class-only review for the shared listing value object used
by both live Trading Post account listings and Trading Post sale-history search results.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_CB1006D489AE13ABBE22`
- field/method proposals: **0**

## Stable ID

`rs/s/t/c` -> `CLIENT_CLASS_000965` -> `TradingPostListing`

## Existing Trading Post authority

Earlier reviews already recover the surrounding feature:

- `TradingPostCurrency`;
- `TradingPostListingPanel`;
- `TradingPostListingsPanel`;
- `TradingPostPanel`;
- `TradingPostPlugin`;
- `TradingPostPacketHandler`;
- `TradingPostSearchPanel`;
- `TradingPostSearchResultPanel`.

The remaining `rs/s/t/c` record is consumed by both halves of that reviewed UI.

## Live account-listing producer

ScriptPacket **30**, already reviewed as `TradingPostPacketHandler`, constructs
`rs/s/t/c` for a live account listing.

Its packet mode populates:

- item id;
- sold/current quantity state;
- total amount;
- price;
- `TradingPostCurrency`;
- item name resolved from the exact item definition.

The completed record is passed directly to `TradingPostListingsPanel`.

## Sale-history search producer

`TradingPostSearchPanel` also constructs `rs/s/t/c`, independently, while decoding exact
sale-history JSON.

The exact surviving JSON keys are:

- `id`;
- `item_id`;
- `time`;
- `item_name`;
- `seller`;
- `buyer`;
- `currency`;
- `price`;
- `amount`.

Those records are then rendered as `TradingPostSearchResultPanel` rows.

## Exact consumers

`TradingPostListingPanel` consumes the same record for active account listings and renders:

- item name and item image;
- sold-versus-amount state;
- currency icon;
- `Price each:`;
- `Received:`;
- a total-value product from price and amount.

The search panel uses the same item id to obtain the Trading Post item image and forwards the
record's item name, price, amount, timestamp, currency, seller and buyer values into each
search-result row.

## Responsibility boundary

The class is a plain value object:

- Strings and integers for the listing/search record;
- one `TradingPostCurrency`;
- getters/setters;
- one total-value calculation;
- fallback item-name resolution from the item id.

It has no rendering, network, plugin lifecycle or unrelated gameplay behavior.

## Naming boundary

`TradingPostListing` is **0.999**.

The noun deliberately covers both current account listings and historical search-result
records because exact v308 uses the same model for both.

The readable name is not claimed as a surviving original developer identifier.

R194 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R194. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_CB1006D489AE13ABBE22`.
