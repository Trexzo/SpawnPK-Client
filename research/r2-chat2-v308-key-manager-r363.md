# Chat 2 — RuneLite key input framework R363

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/g/a/a` -> `CLIENT_CLASS_000178` -> `KeyListener`
- `rs/g/a/b` -> `CLIENT_CLASS_000179` -> `KeyManager`
- review: `SEMREVIEW_C2807DE475FD66EF7AE7`

## Exact retained identity

This pair is not merely descriptively similar to RuneLite input infrastructure. Exact v308
retains highly specific source fingerprints from RuneLite's
`net.runelite.client.input.KeyManager`:

- `Registering key listener: {}`
- `Unregistered key listener: {}`
- `Processing key pressed {} for key listener {}`
- `Consuming key pressed {} for key listener {}`
- matching released/typed variants.

The implementation also retains the same CopyOnWriteArrayList listener registry and
consumed-event short-circuit behavior.

The listener interface directly extends `java.awt.event.KeyListener` and adds the default
login-screen enablement predicate returning false, matching RuneLite `KeyListener`.

## Boundary

These are recovered upstream framework identities, not invented SpawnPK business-domain
names. R363 remains non-canonical semantic research only.
