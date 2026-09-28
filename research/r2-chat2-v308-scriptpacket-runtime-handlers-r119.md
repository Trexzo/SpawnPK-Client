# Chat 2 — exact-v308 ScriptPacket runtime handlers R119

Exact client authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R119 is a separate non-canonical class-only review for three direct R115 ScriptPacket handlers whose runtime consumers remove the remaining domain ambiguity.

## Result

- proposals: **3**
- unresolved: **0**
- review: `SEMREVIEW_1C7B6CB14E9DAFE8553E`
- post-R2 field/method proposals: **0**

## ScriptPacket 21 — NpcHitmarkQueueClearPacketHandler

`rs/q/a/a/a/c` -> `CLIENT_CLASS_000748`.

The packet reads an NPC index, resolves R30 `Npc`, accesses its R33 `HitmarkManager` and clears the CopyOnWriteArrayList R33 identifies as the overflow/replay hitmark queue.

## ScriptPacket 29 — MusicTrackPacketHandler

`rs/q/a/a/a/m` -> `CLIENT_CLASS_000758`.

The packet reads a track id and calls the same Client music-request method used by native client opcode 74. Both paths request OnDemandFetcher type 2; completed matching data is forwarded into the client's byte-array audio/MIDI loader.

## ScriptPacket 43 — NpcOverheadIconPacketHandler

`rs/q/a/a/a/j` -> `CLIENT_CLASS_000755`.

The handler owns an NPC-definition-id -> icon-index override map. Client NPC overhead rendering consumes that map to select a sprite rendered above the NPC; absent an override it falls back to the NpcDefinition's built-in overhead-icon index.

## Boundary

The names for IDs 21 and 43 are descriptive, so confidence is **0.998**. MusicTrackPacketHandler is **0.999** because ScriptPacket 29 exactly shares the native music packet/request pipeline.

Other remaining direct handlers are withheld until their target fields/subsystems are equally precise.

## Acceptance

Chat 2 does not promote R119. Main/Core may accept any subset only through an explicit `semantic_acceptance_spec` bound to `SEMREVIEW_1C7B6CB14E9DAFE8553E`.
