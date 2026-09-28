# Chat 2 — exact-v308 scrolling text R316

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

The Library `client(6).jar` was materialized and SHA-256 verified before this pass.

## Deterministic review result

- `rs/l/e/l` -> `CLIENT_CLASS_000433` -> `ScrollingTextEntry`
- `rs/l/e/m` -> `CLIENT_CLASS_000434` -> `ScrollingTextManager`
- review: `SEMREVIEW_E2874B79B08C787C2E70`
- unresolved: **0**
- member proposals: **0**

## Exact entry state

`rs/l/e/l` has exactly three instance fields:

- one String;
- x integer;
- y integer.

Its constructor stores the supplied String and fixes:

- x = **522**
- y = **330**

It has no second behavior or unrelated state.

## Exact manager lifecycle

`rs/l/e/m` owns:

- one active `rs/l/e/l`;
- one `List<rs/l/e/l>`;
- the live `Client`.

Its String-taking method appends a new entry to that list.

The no-arg update/render method:

1. promotes the oldest queued String when no entry is active;
2. asks `Client.gm` for the rendered text width;
3. terminates the active entry after its x coordinate reaches the negative text width;
4. otherwise decrements x by exactly one;
5. draws the String at the entry x/y coordinates in white.

This is a complete right-to-left scrolling-text lifecycle.

## Exact client ownership

Client constructs exactly one `rs/l/e/m` during initialization.

The central `rs/l/b/b` game/render path invokes the manager every frame immediately beside
the already-recovered hit-drop and experience-drop managers.

A whole-`rs/**` class-file reference scan finds the `rs/l/e/m` type only in:

- `rs/Client`;
- `rs/l/b/b`;
- its own class.

No surviving exact-v308 internal direct caller of the String enqueue method fixes a narrower
feature/domain identity.

## Naming boundary

The names are deliberately generic:

- `ScrollingTextEntry`
- `ScrollingTextManager`

They describe exact behavior without inventing a product-specific feature noun or claiming
lost original identifiers.

Confidence is **0.997** for both.

## Acceptance boundary

R316 is non-canonical semantic research only. Chat 2 performs no acceptance or source
rewrite.
