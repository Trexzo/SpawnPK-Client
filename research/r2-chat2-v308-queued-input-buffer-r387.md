# Chat 2 — R387 duplicate queued-input audit

R387 retains **no semantic proposal**.

The attempted exact-v308 proposals:

- `rs/m/a` -> `CLIENT_CLASS_000522` -> `QueuedInputBuffer`
- `rs/m/a$a` -> `CLIENT_CLASS_000523` -> `QueuedInputEvent`

were rejected by the repository-wide uniqueness guard because the exact same owners/stable IDs
were already reviewed in **R282**.

The R387 candidate JSON, semantic-review JSON and deterministic test are therefore removed.
Any useful queue/input behavioral evidence remains corroboration for the authoritative R282
ownership only.

R387 is a zero-retained duplicate audit. No acceptance or source rewrite is performed.
