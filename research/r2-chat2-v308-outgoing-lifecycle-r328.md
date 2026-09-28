# Chat 2 — post-merge outgoing lifecycle packets R328

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

PR #9 was merged before this batch. R328 starts the post-merge Chat 2 branch from current Main.

## Result

- `rs/o/a/a/a/d` -> `CLIENT_CLASS_000690` -> `IdleKeepalivePacket` (C2S 0)
- `rs/o/a/a/a/q` -> `CLIENT_CLASS_000703` -> `RegionLoadingFinishedAckPacket` (C2S 121)
- `rs/o/a/a/a/U` -> `CLIENT_CLASS_000733` -> `IdleLogoutNoticePacket` (C2S 202)
- `rs/o/a/a/a/W` -> `CLIENT_CLASS_000735` -> `RegionChangeAckPacket` (C2S 210)

Review: `SEMREVIEW_D5F4C9121A96681B2774`

## Exact authority

The cumulative exact-current C2S table fixes:

- opcode 0 — IDLE_KEEPALIVE — fixed 0;
- opcode 121 — REGION_LOADING_FINISHED_ACK — fixed 0;
- opcode 202 — IDLE_LOGOUT_NOTICE — fixed 0;
- opcode 210 — REGION_CHANGE_ACK — fixed 4 / i32.

LocalLab runtime independently observed repeated opcode-0 keepalive traffic and repeated
opcode-121 `loadingAck=true` traffic. The earlier half-connected LocalLab freeze was traced
to an unframed opcode-202 idle logout notice, further corroborating that contract.

## Withheld serializer-only objects

The exact protocol master explicitly marks four packet serializers as dormant and without
stock-client references outside their own serializer classes:

- opcode 2 — `DORMANT_CUSTOM_U16_O`
- opcode 6 — `DORMANT_CUSTOM_U16_P`
- opcode 78 — `DORMANT_CUSTOM_EMPTY_G`
- opcode 109 — `DORMANT_CUSTOM_SIX_SHORT_X`

Those structural labels are not useful enough to become semantic class names. R328 therefore
leaves `rs/o/a/a/a/o`, `p`, `g`, and `x` unnamed.

R328 is non-canonical semantic research only.
