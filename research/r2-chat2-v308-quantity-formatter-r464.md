# Chat 2 — exact-v308 QuantityFormatter R464

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/A/p` -> `CLIENT_CLASS_000019` -> `QuantityFormatter`
- proposal: `SEMPROP_7BB3024033EBBDFCF3B4`
- review: `SEMREVIEW_2044CC3C307F95341520`

## Exact v308 surface

The class owns the full quantity formatting/parsing utility surface:

- long quantity -> abbreviated stack string;
- int quantity -> RuneScape-style decimal stack string;
- optional precise decimal formatting;
- abbreviated String -> long parsing;
- plain comma-delimited long formatting;
- plain comma-delimited double formatting.

Its suffix table is:

- empty
- K
- M
- B
- T

Its validation pattern is exactly:

`^-?[0-9,.]+([a-zA-Z]?)$`

Surviving failure text includes:

- `<value> does not resemble a properly formatted stack.`
- `Invalid Suffix: <suffix>`

## Upstream identity

RuneLite's `net.runelite.client.util.QuantityFormatter` carries the same API/algorithm,
including the same validation regex, failure strings, English-locale NumberFormat,
`#,###.#` / `#,###.###` decimal formats, stack abbreviation, parsing and number-format
helpers.

SpawnPK's exact-v308 copy extends the suffix table with `T`; that fork-local extension does
not change the class identity.

## Exact live consumers

Only the `rs/s/t/*` trading/price presentation family directly references this class in
exact v308.

Those consumers use it for:

- price-each values;
- received values;
- displayed stack quantities;
- multiplied quantity/value totals.

## Boundary

R464 is non-canonical semantic research only. No member proposals or source rewrite are
performed.
