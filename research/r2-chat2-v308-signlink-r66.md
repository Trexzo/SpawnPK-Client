# Chat 2 — exact-v308 Signlink semantics R66

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R66 is a separate non-canonical class-only semantic review batch in the classic runtime /
platform bridge lane.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_3F05C7C6FE46D833E4E1`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/v/a` -> `CLIENT_CLASS_001106`

## `rs/v/a` -> `Signlink`

The class is a singleton-style runtime service implementing `Runnable`.

Its exact-v308 responsibilities include:

- maintaining a background service thread;
- serializing socket-open requests against a stored `InetAddress`;
- opening remote URL/DataInputStream resources;
- launching supplied Runnable tasks with requested thread priority;
- owning RandomAccessFile cache handles;
- locating/reporting cache/runtime directory information;
- queueing byte-array save requests;
- retaining applet/environment and DNS/reporting state.

Those responsibilities are not generic application utilities; they form the classic client
platform/network/cache bridge historically called `Signlink`.

The exact v308 bytecode role is primary evidence. Historical client naming is corroborating
lineage evidence.

## Duplicate-audit boundary

Before committing this batch, Chat 2 scanned prior R2-R64 review sets for either the
`Signlink` semantic name or owner `rs/v/a`. Neither was previously proposed.

The temporary duplicate R65/R66 rediscoveries were removed before this batch and are not
part of the committed semantic review set.

## Acceptance boundary

Chat 2 does not promote R66. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_3F05C7C6FE46D833E4E1`.
