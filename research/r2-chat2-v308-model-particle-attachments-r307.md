# Chat 2 — exact-v308 model particle attachment config R307

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/r/b` -> `CLIENT_CLASS_000784` -> `ModelParticleAttachmentConfig`
- review: `SEMREVIEW_05C6AA5481B981CF84F7`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

`rs/r/b` owns one static model-id keyed `int[][]` table. Exact entries include model ids **65295**, **65328**, **2467** and **42467**.

R30 `Model` is the only live consumer.

For each table row, Model writes the second value plus one into its per-face array `L`. The first value is either:

- an explicit face index; or
- special selector **-1**, **-2**, **-3** or **-4**, which expands across one or more model face-group arrays before applying the same value.

The semantic identity becomes exact later in the model render path:

1. Model reads `L[face] - 1`.
2. That value indexes the R50 `ParticleDefinition[]` registry.
3. The selected definition is spawned from that face's live geometry through R306 `CpuParticlePool`.
4. The resulting Particle is attached to the Client's per-definition CPU particle renderer.

The table therefore configures model-face/group -> particle-definition attachments. It is not a generic recolor/priority override table.

## Boundary

R307 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.
