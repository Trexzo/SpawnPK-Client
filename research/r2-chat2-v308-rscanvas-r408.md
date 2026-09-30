# Chat 2 — exact-v308 RSCanvas R408

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/b` -> `CLIENT_CLASS_000077` -> `RSCanvas`
- proposal: `SEMPROP_51CFD0CCC2BCF801122D`
- review: `SEMREVIEW_EDCE47ECB8D9925A7E9D`

## Exact v308 shape

`rs/b`:

- extends `java.awt.Canvas`;
- stores one delegated `java.awt.Component`;
- forwards `update(Graphics)` directly to that component;
- forwards `paint(Graphics)` directly to that component.

That defining shape is the classic RuneScape `RSCanvas` wrapper.

## Historical identity

Multiple refactored RuneScape-client sources preserve this class as `RSCanvas`, including
the same component-delegation and paint/update forwarding contract.

## SpawnPK drift

SpawnPK v308 adds modern wrapper behavior:

- focus-state suppression around `removeFocusListener` / `requestFocusInWindow`;
- client-aware resizing through Launcher/Client state;
- ordinary Canvas location forwarding.

Those extensions do not change the historical class identity.

## Boundary

R408 recovers the class identity only. No field or method semantic proposals are created.

R408 remains non-canonical Chat 2 research.
