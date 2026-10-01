# Chat 2 — exact-v308 RuneLite utility identities R466

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/A/q` -> `CLIENT_CLASS_000020` -> `ReflectUtil`
- `rs/A/s` -> `CLIENT_CLASS_000024` -> `Text`
- `rs/A/t` -> `CLIENT_CLASS_000025` -> `WildcardMatcher`
- review: `SEMREVIEW_CB92D15B462A836B81C7`

## ReflectUtil

Exact v308 preserves the RuneLite reflection helper surface:

- MethodHandles lookup/private lookup support;
- lookup-helper installation;
- declared constructor/field/method access;
- class-resource byte loading;
- reflective construction/accessibility helpers.

It also preserves the exact failure literal:

`unable to install lookup helper`

This matches RuneLite `net.runelite.client.util.ReflectUtil`.

## Text

Exact v308 owns the broad shared text utility surface:

- RuneScape markup stripping/normalization;
- `<lt>`, `<gt>`, `<br>`, `<img...` handling;
- whitespace/name normalization;
- collection/CSV helpers;
- enum/display-name formatting;
- Jaro-Winkler fuzzy comparison.

The class preserves RuneLite's exact `<[^>]*>` tag pattern and the same
`JaroWinklerDistance` utility dependency.

This matches RuneLite `net.runelite.client.util.Text`.

## WildcardMatcher

Exact v308 converts case-insensitive star-wildcard patterns into quoted regular expressions
and replaces wildcards with `.*` before matching.

This matches RuneLite `net.runelite.client.util.WildcardMatcher`.

## Boundary

All three names are source-backed identities, not descriptive inventions.

R466 remains non-canonical semantic research only.
