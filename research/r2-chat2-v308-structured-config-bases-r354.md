# Chat 2 — R354 duplicate structured-config audit

R354 retains **no semantic proposals**.

Two exact-v308 abstractions were rediscovered, but both already have prior ownership:

- `rs/t/a` -> **R248**
- `rs/t/c` -> **R247**

The fresh evidence strengthens those older reviews.

For `rs/t/a`:

- dual source/compiled config paths;
- YAML loading/writing through SnakeYAML;
- compiled loading through MessagePack;
- canonical `Map<Integer, Map<String,Object>>` payload.

For `rs/t/c<T>`:

- typed config-to-object mapper contract;
- per-id materialization into an int-keyed cache;
- concrete animation/NPC/GFX/item/object definition specializations;
- shared primitive/nested-array conversion helpers.

The attempted R354 candidate/review/test artifacts are removed. No new semantic ownership
is retained.
