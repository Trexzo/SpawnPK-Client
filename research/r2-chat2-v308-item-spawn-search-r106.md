# Chat 2 — exact-v308 item spawn search result R106

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R106 is a separate non-canonical class-only review for the live item-spawn search result
value object.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_F7E321738CA3464384DD`
- field/method proposals: **0**
- confidence: **0.998**

## Stable ID

- `rs/s` -> `CLIENT_CLASS_000853` -> `ItemSpawnSearchResult`

## Exact value-object shape

The class contains exactly:

- one String;
- one int.

Its constructor stores those two values and its two accessors return them unchanged.

That shape alone would be ambiguous; the live consumers remove the ambiguity.

## Exact spawn-tab construction

The spawn/search controller `rs/n/c/af` exposes the surviving strings:

- `Click the search button`;
- `Please have at least 3 letters in your search term!`;
- `Search`;
- `Spawn this item`.

Its live search method iterates item definitions and constructs `rs/s` from:

- the matched ItemDefinition display name;
- the matched ItemDefinition integer ID.

The result objects are accumulated into the controller's static search-result list.

## Exact UI consumption

When rebuilding result rows, the same controller reads:

- `rs/s.b()` as the item ID and uses it to configure the item/model widget;
- `rs/s.a()` as the visible result text rendered next to the action
  `Spawn this item`.

The controller also stores the result object in its generated-widget lookup map.

This independently fixes both fields and the overall class role as one item-spawn search
result.

## Naming boundary

No surviving original source noun was found.

`ItemSpawnSearchResult` is therefore descriptive exact-behavior recovery rather than a
claim about the original developer identifier. Confidence is 0.998.

R106 remains class-only; no field/accessor semantic proposals are introduced.

## Acceptance boundary

Chat 2 does not promote R106. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F7E321738CA3464384DD`.
