# Chat 2 — exact-v308 Plugin Hub / Item Search / Trading Post semantics R13

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R13 is another separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior Chat 2 review batches.

## Deterministic review result

- candidate classes: **10**
- resolved proposals: **10**
- unresolved: **0**
- review ID: `SEMREVIEW_D9B003FC41F9A1D776D9`
- field/method proposals: **0**

## Plugin Hub / configuration

| Raw class | Stable ID | Candidate semantic |
| --- | --- | --- |
| `rs/s/b/a` | `CLIENT_CLASS_000861` | `PluginConfigurationPanel` |
| `rs/s/b/n` | `CLIENT_CLASS_000874` | `PluginConfigurationDescriptor` |
| `rs/s/b/o` | `CLIENT_CLASS_000875` | `PluginHubPluginEntry` |
| `rs/s/b/q` | `CLIENT_CLASS_000877` | `PluginHubPanel` |
| `rs/s/b/u` | `CLIENT_CLASS_000881` | `PluginEnableToggleButton` |

Strong exact evidence includes the literal title `Plugin Hub`, exact pin/configure/enable
UI text, direct descriptor/config-panel references and the exact self-identifying
`PluginConfigurationDescriptor(...)` toString form.

## Item ID Search

- `rs/s/g/a` -> `ItemIdSearchPanel`
- `rs/s/g/b` -> `ItemIdSearchPlugin`

The runtime class has exact title `Item ID Search`, config key `itemsearch`, panel/nav
ownership and `search.png`. The paired panel owns the search field/results area and exact
login/database/minimum-query validation text.

## Trading Post

- `rs/s/t/g` -> `TradingPostListingsPanel`
- `rs/s/t/h` -> `TradingPostPanel`
- `rs/s/t/i` -> `TradingPostPlugin`

The top-level panel combines exact tabs `Your Listings` and `Search`, where the search side
is the already reviewed R11 `TradingPostSearchPanel`. The listings panel has exact no-listing
account text, while the runtime plugin has exact title/config/navigation strings
`Trading Post`, `tradepost` and `Trading post`.

## Acceptance boundary

Chat 2 does not promote R13. Main/Core may accept any desired subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_D9B003FC41F9A1D776D9`.
