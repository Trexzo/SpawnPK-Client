# Chat 2 — exact-v308 callback registries R339

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/h/a` -> `CLIENT_CLASS_000289` -> `ClientCallbackRegistry`
- `rs/h/c` -> `CLIENT_CLASS_000291` -> `LoggedInClientCallbackRegistry`
- review: `SEMREVIEW_049592478C30C6CB82AC`

R329 already recovers the two callback contracts:

- `rs/h/b` -> `ClientCallback` with `void invoke()`;
- `rs/h/e` -> `ClientLoopCallback` with `boolean loop()`.

Both registries own the same lifecycle shape:

- queued one-shot callbacks;
- keyed one-shot callbacks;
- keyed repeating callbacks;
- repeating callbacks are removed when `loop()` returns false.

The distinction is fixed by Client's main-cycle callsite.

`ClientCallbackRegistry` is drained unconditionally after the main client-step path.

`LoggedInClientCallbackRegistry` is drained immediately afterward only when the client's
logged-in/active state flag is true. Its registrations span the plugin, interface and GPU
runtime surface.

R339 remains non-canonical semantic research only.
