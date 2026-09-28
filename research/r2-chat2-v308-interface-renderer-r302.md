# Chat 2 — exact-v308 central interface renderer R302

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/l/b/d` -> `CLIENT_CLASS_000382` -> `InterfaceRenderer`
- review: `SEMREVIEW_4EF15DF506252869310E`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

The role is fixed by the live render flow rather than package adjacency.

- `Client` exposes an interface-draw wrapper taking screen coordinates, an `rs/n/e` widget and a parent/scroll value; the wrapper delegates directly to `rs/l/b/d.a(Client,int,int,rs/n/e,int)`.
- The renderer walks child widget ids from the live `rs/n/e` table, resolves parent offsets and scroll position, and recursively calls the same interface-render method for nested children.
- Widgets carrying the retained R288 `InterfaceDrawCallback` receive their resolved x/y draw coordinates from this path.
- The same traversal owns clipping plus the concrete presentation branches for live interface text, sprites, inventory/item/model content and hover/selection state.
- Exact widget-scoped strings such as **Click here to continue**, **Please wait...**, bank-specific exceptions and other interface presentation behavior occur inside this renderer.

This is therefore the central client interface/widget renderer, not a domain-specific overlay or a generic graphics utility.

## Deliberate exclusions

`rs/l/b/a` and `rs/l/b/b` remain unnamed in R302. Their broad frame/game-state/HUD responsibilities are visible, but the exact source-level noun boundary between the two is weaker than the direct renderer identity above.

## Boundary

R302 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
