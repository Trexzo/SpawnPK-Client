# Chat 2 — exact-v308 incoming packet definitions R349

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/f/c` -> `CLIENT_CLASS_000173` -> `IncomingPacketDefinitions`
- proposal: `SEMPROP_27A497FC39D471243BA7`
- review: `SEMREVIEW_FA7875609345B70BABBB`

## Opcode catalog

The class is almost entirely public static final integer constants. Their values line up
directly with independently established server-to-client contracts, for example:

- 219 — close interfaces
- 27 — amount-input prompt
- 50 — friend status update
- 44 — ground-item spawn
- 117 — projectile
- 241 — constructed/instanced region change
- 253 — request/server-message directive transport

This is therefore not a generic constants bag.

## Raw length definitions

The class also creates a 256-entry integer array indexed by incoming opcode.

Exact examples:

- 34 -> -2
- 53 -> -2
- 81 -> -2
- 126 -> -2
- 196 -> -1
- 214 -> -2
- 241 -> -2
- 253 -> -1

Fixed-length entries carry their literal byte lengths.

Those `-1` and `-2` values are the same variable-byte / variable-short framing
sentinels used by the exact Client inbound parser.

## Relationship to R342

R342 names `rs/f/d` as `IncomingPacketLengthTable`, the exact table directly indexed
by the Client after decoding the incoming opcode.

R349 is intentionally different: `rs/f/c` is the static raw packet-definition catalog
combining protocol opcode constants and raw opcode-length definitions. It owns no dispatch
or decode behavior itself.

## Boundary

The class-level name is proposed only. Individual constant fields remain obfuscated and are
not separately proposed.

R349 is non-canonical semantic research only.
