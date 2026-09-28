# Chat 2 — exact-v308 historical RuneLite plugin search recovery R238

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_FD1DEEC1C24C0042C027`
- field/method proposals: **0**

## Stable IDs

- `rs/s/b/t` -> `CLIENT_CLASS_000880` -> `PluginSearch`
- `rs/s/b/v` -> `CLIENT_CLASS_000882` -> `SearchablePlugin`

## Historical source identity

RuneLite source at `68c819924cfd6bfb4848c71f74c121109f289d5a` predates the May 2025 install-count ranking change and matches
exact v308.

`PluginSearch` preserves:

- the single-space Guava Splitter with trim/omit-empty;
- generic search over `SearchablePlugin`;
- lowercased term filtering;
- blank-query pinned/name ordering with null-safe comparators;
- nonblank exact-name, name-piece, keyword-piece, pinned and name ordering;
- iterable-to-stream and containment helpers.

`SearchablePlugin` preserves exactly:

- `getSearchableName()`;
- `getKeywords()`;
- default `isPinned()` returning false.

Current RuneLite later adds `installs()`; exact v308 does not, which fixes the historical
source window rather than weakening the match.

## Acceptance boundary

Chat 2 does not promote R238. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_FD1DEEC1C24C0042C027`.
