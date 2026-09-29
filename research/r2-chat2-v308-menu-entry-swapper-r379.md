# Chat 2 — Menu Entry Swapper source identities R379

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/l/b` -> `CLIENT_CLASS_000927` -> `MenuEntrySwapperConfig`
- `rs/s/l/c` -> `CLIENT_CLASS_000928` -> `MenuEntrySwapperPlugin`
- review: `SEMREVIEW_5D457783633127AFEF72`

## Exact/source join

Exact v308 preserves:

- plugin name `Menu Entry Swapper`;
- exact descriptor `Change the default option that is displayed when hovering over objects`;
- config group `menuentryswapper`;
- `Item Swaps` / `NPC Swaps`;
- left-click and shift-click customization controls;
- live `MenuHover` / `MenuOpened` processing.

RuneLite historical source preserves the same plugin/config names and the distinctive descriptor/config strings.

## Existing helper ownership

`rs/s/l/a` was already reviewed in R186 as `MenuEntryEntityMatcher`, based on its surviving `isMatchingEntity(int, int)` method and complete MenuEntrySwapper call graph. R379 therefore adds only the source-proven config/plugin identities and does not duplicate that helper.

R379 remains non-canonical semantic research only.
