# Chat 2 — exact-v308 config map type references R337

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/t/b` -> `CLIENT_CLASS_000990` -> `IntegerConfigMapTypeReference`
- `rs/t/d` -> `CLIENT_CLASS_000994` -> `StringConfigMapTypeReference`
- review: `SEMREVIEW_926C5322EA2395C46095`

## IntegerConfigMapTypeReference

The class has no state or custom behavior beyond its exact generic superclass:

`TypeReference<Map<Integer, Map<String, Object>>>`

R248 `ConfigDataMapper` creates it directly for the compiled MessagePack read path.
The decoded value is the integer-keyed raw config corpus consumed by R247
`DefinitionConfigLoader` and its reviewed definition-loader subclasses.

## StringConfigMapTypeReference

This class likewise has only its exact generic signature:

`TypeReference<Map<String, Map<String, Object>>>`

R81 `WanderingMerchantItemConfigLoader` creates it for the compiled
`wandering_merchant` MessagePack path and then traverses the returned string-keyed sections,
including the nested exact key `items`.

## Boundary

These are deliberately mechanical type-token names, not invented business-domain classes.
R337 remains non-canonical semantic research only.
