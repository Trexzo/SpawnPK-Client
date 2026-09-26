# Chat 2 — exact-v308 TradingPostConfig R246

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_FE1AC254862559A96E7C`
- field/method proposals: **0**

## Stable identity

`rs/s/t/a` -> `CLIENT_CLASS_000963` -> `TradingPostConfig`

Exact v308 marks this public interface with the runtime config-group annotation:

`tradepost`

The package sequence then continues directly into the independently reviewed Trading Post family:

- `rs/s/t/b` -> `CLIENT_CLASS_000964` -> `TradingPostCurrency`
- `rs/s/t/c` -> `TradingPostListing`
- `rs/s/t/d` -> `TradingPostListingPanel`
- `rs/s/t/g` -> `TradingPostListingsPanel`
- `rs/s/t/h` -> `TradingPostPanel`
- `rs/s/t/i` -> `TradingPostPlugin`
- `rs/s/t/j` -> `TradingPostPacketHandler`
- `rs/s/t/l` -> `TradingPostSearchPanel`
- `rs/s/t/m` -> `TradingPostSearchResultPanel`

The v308 interface currently declares no config methods, so R246 claims only the exact subsystem/config identity and no invented settings.

The remaining local holdouts are implementation helpers:

- `rs/s/t/e`: mouse adapter bound to `TradingPostListingPanel`;
- `rs/s/t/k`: compiler-generated enum switch map;
- `rs/s/t/n`: mouse adapter bound to `TradingPostSearchResultPanel`.

They remain deliberately unnamed.

## Acceptance boundary

R246 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
