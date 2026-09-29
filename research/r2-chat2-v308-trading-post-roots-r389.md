# Chat 2 — Trading Post root identities R389

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/t/h` -> `CLIENT_CLASS_000970` -> `TradingPostPanel`
- `rs/s/t/i` -> `CLIENT_CLASS_000971` -> `TradingPostPlugin`
- review: `SEMREVIEW_B4AA6950E8C8ACEF4A97`

Existing Trading Post ownership is preserved:

- R246 `TradingPostConfig`
- R194 `TradingPostListing`
- R195 `TradingPostListingImageLoader`

The main panel exposes exact `Your Listings` / `Search` tabs; the plugin wrapper carries
the `Trading Post` identity and `ge_icon.png` navigation lifecycle.

R389 remains non-canonical semantic research only.
