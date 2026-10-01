# Chat 2 — R394 duplicate AdventureOrbRenderer audit

R394 retains **no semantic proposal**.

The attempted proposal:

- `rs/i/b`
- `CLIENT_CLASS_000297`
- attempted descriptive label: `GameframeControlRenderer`

duplicates the original accepted R2 semantic seed, where the exact same stable class is already
owned as:

- `rs/i/b` -> `CLIENT_CLASS_000297` -> `AdventureOrbRenderer`

The broader exact-v308 evidence discovered in R394 is still useful corroboration for that
existing authority:

- the class owns HP/prayer/run/spec and custom gameframe orb assets;
- it owns adventure/promo/event and multiple toggle controls;
- it owns gameframe chat-button/hover-chat assets;
- Client routes chat-channel/control interactions into the same class;
- GameHudRenderer and multiple overlays query its live layout/control state.

That evidence shows the accepted `AdventureOrbRenderer` has grown into a broader gameframe
control responsibility in exact v308, but it does **not** justify creating a second semantic
identity for the same stable class.

The R394 candidate/review/test artifacts are removed. R394 remains only as this
zero-retained duplicate/corroboration audit.

No acceptance or source rewrite is performed.
