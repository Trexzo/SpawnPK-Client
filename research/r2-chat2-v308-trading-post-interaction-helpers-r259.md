# Chat 2 — exact-v308 Trading Post interaction helpers R259

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/s/t/e` -> `CLIENT_CLASS_000967` -> `TradingPostListingInteractionListener`
- `rs/s/t/n` -> `CLIENT_CLASS_000976` -> `TradingPostSearchResultHoverListener`
- review: `SEMREVIEW_6E9A005C2F1367BF545D`
- unresolved: **0**
- field/method proposals: **0**

## Exact bytecode proof

The saved Library `client(6).jar` was re-verified before this batch:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

### Listing panel adapter

`rs/s/t/e` extends `MouseAdapter` and owns exactly one reviewed
`TradingPostListingPanel`.

Its complete live behavior is:

- left-button `mousePressed` -> invoke the panel action path;
- `mouseEntered` -> set the owned JPanel to the exact Trading Post hover color;
- `mouseExited` -> restore the exact normal panel color.

This is therefore a bounded click/hover interaction adapter for one listing panel.

### Search-result hover adapter

`rs/s/t/n` extends `MouseAdapter` and owns:

- one reviewed `TradingPostSearchResultPanel`;
- one `List<JPanel>`;
- one captured base `Color`.

On enter it recolors every listed JPanel to the exact hover color and sets the parent
cursor to `HAND_CURSOR` (12). On exit it restores the captured base color and
`DEFAULT_CURSOR` (0). Its `mouseReleased` implementation is empty.

No unrelated exact-v308 consumer survives.

## Naming boundary

Both R259 names are descriptive exact-behavior recoveries for anonymous/helper classes.
They do not claim verbatim original source identifiers.

The adjacent `rs/s/t/k` remains excluded because it is a compiler-generated enum switch map.

## Acceptance boundary

R259 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
