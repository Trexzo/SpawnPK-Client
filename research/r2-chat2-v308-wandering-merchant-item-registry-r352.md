# Chat 2 — wandering merchant item registry R352

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/t/a/g` -> `CLIENT_CLASS_000989` -> `WanderingMerchantItemRegistry`
- proposal: `SEMPROP_1745F265E82AA47A04BE`
- review: `SEMREVIEW_486675F3026DFE05BE35`

## Exact config source

The class extends the shared config-file loader family and points at:

- `configs/wandering_merchant.yaml`
- compiled fallback `configs/w.bin`

It walks each merchant map's nested `items` entries and reads their `id` values.

## Item normalization

Before adding an ID, the loader resolves the exact ItemDefinition redirect used by noted /
certificate-like forms when present, except for ids:

- 995
- 20693
- 20842

The resulting ids populate one static integer set.

## Live consumer

Client constructs and loads this registry during startup.

The only external runtime consumer is item-name rendering. When the associated client-side
config flag is enabled and the current item id belongs to the registry, the display string
is decorated with exact marker:

`<img=370>`

No exact-v308 code in this class owns merchant rotation, stock, pricing or transaction
authority.

## Boundary

`WanderingMerchantItemRegistry` is therefore the narrow exact role: a config-derived
item-ID registry used for client presentation.

R352 remains non-canonical semantic research only.
