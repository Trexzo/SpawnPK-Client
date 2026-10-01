# Chat 2 — exact-v308 ObjectDefinition customizer R349

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/c/a/a` -> `CLIENT_CLASS_000080` -> `ObjectDefinitionCustomizer`
- proposal: `SEMPROP_9F66DC3A286621E5BCF0`
- review: `SEMREVIEW_D6180AAE947BCEF5D390`

## Exact target

The class imports only `rs.d.r` and all mutation entry points accept an `rs.d.r`
definition plus its numeric definition id.

The exact-v308 target owns the object-definition model/action/transform state and is paired
with the already-recovered R80 `ObjectDefinitionConfigLoader` at `rs/t/a/f`.

## Exact override surface

Recovered source size is roughly 72 KB.

The common mutation method contains a hard-coded switch over approximately **680 object ids**
and mutates definition fields for those ids.

The public apply path then layers additional exact special cases, including model-array
replacements for:

- 6926
- 11986
- 38847 / 38848
- 41451 / 41453
- 42517 / 42518

This is post-decode customization, not cache parsing or lookup.

## Boundary

The class owns no instance state and no independent cache. The name describes the exact
static override role only.

R349 is non-canonical semantic research.
