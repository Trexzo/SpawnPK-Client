# Chat 2 — post-merge outgoing packet residuals R328

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

PR #9 was merged before this batch. R328 starts the post-merge Chat 2 continuation from current Main.

## Result

- `rs/o/a/a/a/d` -> `CLIENT_CLASS_000690` -> `IdleKeepalivePacket` (C2S0)
- `rs/o/a/a/a/q` -> `CLIENT_CLASS_000703` -> `RegionLoadingFinishedAckPacket` (C2S121)
- `rs/o/a/a/a/r` -> `CLIENT_CLASS_000704` -> `PlayerOption3Packet` (C2S73)
- `rs/o/a/a/a/T` -> `CLIENT_CLASS_000732` -> `PlayerOption2Packet` (C2S153)
- `rs/o/a/a/a/U` -> `CLIENT_CLASS_000733` -> `IdleLogoutNoticePacket` (C2S202)

Review: `SEMREVIEW_2369781C7646FAB1A15E`

## Explicitly withheld residuals

- C2S2 / `rs/o/a/a/a/o`: dormant custom u16 serializer.
- C2S6 / `rs/o/a/a/a/p`: dormant custom u16 serializer.
- C2S78 / `rs/o/a/a/a/g`: dormant custom empty serializer.
- C2S109 / `rs/o/a/a/a/x`: dormant custom six-short serializer.
- C2S210 / `rs/o/a/a/a/W`: generated object writes only opcode 210, while the live exact-current REGION_CHANGE_ACK contract is four bytes; it is stale/incomplete and is not assigned the live contract name.
- C2S128 and C2S139 each have duplicate generated packet classes with identical serialization and no exact ownership discriminator, so no arbitrary duplicate receives the canonical-looking slot name.

R328 remains non-canonical semantic research only.
