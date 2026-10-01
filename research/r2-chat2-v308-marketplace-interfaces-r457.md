# Chat 2 — exact-v308 SpawnPK Marketplace interfaces R457

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/as` -> `CLIENT_CLASS_000623` -> `SpawnPKMarketplaceInterface`
- `rs/n/c/at` -> `CLIENT_CLASS_000624` -> `MarketplaceSearchResultsInterface`
- `rs/n/c/au` -> `CLIENT_CLASS_000625` -> `MarketplaceListingInterface`
- review: `SEMREVIEW_CA1AD5423E9AD89F79E6`

The three builders are distinct custom-interface-registry screens and are separate from the
RuneLite-style Trading Post plugin.

Main screen anchors include `SpawnPK Marketplace`, Search item/user, Sell item, View
listings, recent sales and personal history/sales.

Search-results anchors include `SpawnPK Marketplace Search Results`, pagination,
Name/Quantity, Seller, Total offers, sorting and listing selection.

Listing-screen anchors include `SpawnPK Marketplace Listing`, Set price, Set quantity,
currency selection, Submit and item-history controls.

## Boundary

R457 recovers client presentation only. Listings, prices, currency balances, search data,
purchase/sale execution and settlement remain server authority.

R457 remains non-canonical Chat 2 research only.
