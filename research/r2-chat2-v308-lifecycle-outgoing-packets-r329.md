# Chat 2 — lifecycle/control outgoing packets R329

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/o/a/a/a/d` -> `CLIENT_CLASS_000690` -> `IdleKeepalivePacket` (opcode 0)
- `rs/o/a/a/a/q` -> `CLIENT_CLASS_000703` -> `RegionLoadingFinishedAckPacket` (opcode 121)
- `rs/o/a/a/a/U` -> `CLIENT_CLASS_000733` -> `IdleLogoutNoticePacket` (opcode 202)
- `rs/o/a/a/a/W` -> `CLIENT_CLASS_000735` -> `RegionChangeAckPacket` (opcode 210)
- review: `SEMREVIEW_D5F4C9121A96681B2774`

## Exact contracts

### Opcode 0

The generated class has no fields and writes only opcode 0.

The exact-current C2S master table identifies opcode 0 as:

`IDLE_KEEPALIVE / FIXED 0`

### Opcode 121

The generated class has no fields and writes only opcode 121.

The exact-current C2S master table identifies opcode 121 as:

`REGION_LOADING_FINISHED_ACK / FIXED 0`

### Opcode 202

The generated class has no fields and writes only opcode 202.

The exact-current C2S master table identifies opcode 202 as:

`IDLE_LOGOUT_NOTICE / FIXED 0`

This is independently corroborated by the prior LocalLab runtime freeze investigation, where
the client emitted opcode 202 after extended idle time and an older decoder paused because
the fixed-zero framing entry was missing.

### Opcode 210

The generated class writes:

1. opcode 210;
2. constant i32 `1057001181`.

The exact-current C2S master table identifies opcode 210 as:

`REGION_CHANGE_ACK / FIXED 4 / i32_be`

The generated object has no constructor fields, so the acknowledgement payload is invariant.

## Boundary

These are session/lifecycle packets, not gameplay services.

Four serializer-only residual opcodes `2/6/78/109` remain deliberately unnamed beyond
their structural dormant contracts because exact v308 contains no stock-client references
outside their serializer classes.

R329 remains non-canonical semantic research only.
