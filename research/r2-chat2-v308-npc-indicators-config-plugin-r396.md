# Chat 2 — R396 duplicate NPC Indicators audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R396 retains **no semantic proposal**.

The original R396 attempt re-proposed two already-owned exact-v308 classes:

- `rs/s/o/d` / `CLIENT_CLASS_000944` / `NpcIndicatorsConfig`
- `rs/s/o/e` / `CLIENT_CLASS_000945` / `NpcIndicatorsPlugin`

Current-Main reconciliation exposed the duplicates through the repository-wide semantic
uniqueness gate.

## Existing authorities

### Configuration

R4 already owns the exact config class:

- proposal: `SEMPROP_3EA119C8462103D4B8A1`
- review: `SEMREVIEW_DE8D18FF905B89D02488`
- owner: `rs/s/o/d`
- stable id: `CLIENT_CLASS_000944`
- name: `NpcIndicatorsConfig`

R4 already fixes the literal `npcindicators` group and its highlight/render configuration
surface.

### Plugin

R9 already owns the exact plugin class:

- proposal: `SEMPROP_58AF0A206F7EA87B06E6`
- review: `SEMREVIEW_F015AA6B979CF43ECBE6`
- owner: `rs/s/o/e`
- stable id: `CLIENT_CLASS_000945`
- name: `NpcIndicatorsPlugin`

R9 already fixes the NPC Indicators runtime/plugin identity and pairing with the R4 config.

## Corroborating evidence retained

The later R396 investigation remains useful only as corroboration:

- exact menu vocabulary: `Tag`, `Un-tag`, `Tag-All`, `Un-tag-All`;
- exact render-style vocabulary: `hull`, `tile`, `truetile`, `swtile`,
  `swtruetile`, `outline`;
- ConfigChanged / GameStateChanged / NpcSpawned / MenuHover event surface;
- joins to R189 NpcIndicatorsOverlay, R26 HighlightedNpc and R243 MemorizedNpc.

These facts strengthen the existing R4/R9 authority. They do not create a second semantic
identity.

## CI evidence

The post-Main reconciliation uniqueness gate correctly failed the duplicate R396 attempt.
The subsequent partial correction that retained only `NpcIndicatorsPlugin` is also invalid,
because R9 already owns that exact owner/name/stable-id.

R396 is therefore closed as a correction/audit batch only.

No candidate JSON, semantic-review JSON, acceptance spec or source rewrite is retained.
