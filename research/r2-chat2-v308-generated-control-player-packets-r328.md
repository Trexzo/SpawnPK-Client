# Chat 2 — remaining exact generated control/player packets R328

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/o/a/a/a/d` / 000690 / opcode 0 -> `IdleKeepalivePacket`
- `rs/o/a/a/a/q` / 000703 / opcode 121 -> `RegionLoadingFinishedAckPacket`
- `rs/o/a/a/a/r` / 000704 / opcode 73 -> `PlayerOption3Packet`
- `rs/o/a/a/a/T` / 000732 / opcode 153 -> `PlayerOption2Packet`
- `rs/o/a/a/a/U` / 000733 / opcode 202 -> `IdleLogoutNoticePacket`
- `rs/o/a/a/a/W` / 000735 / opcode 210 -> `RegionChangeAckPacket`

Review: `SEMREVIEW_DD2918DAD97E0DF32AAC`

## Exact-current contracts

The C2S master table fixes:

- opcode 0 as `IDLE_KEEPALIVE`;
- opcode 73 as `PLAYER_OPTION_3`;
- opcode 121 as `REGION_LOADING_FINISHED_ACK`;
- opcode 153 as `PLAYER_OPTION_2`;
- opcode 202 as `IDLE_LOGOUT_NOTICE`;
- opcode 210 as `REGION_CHANGE_ACK`.

The generated classes serialize exactly those fixed opcodes. The player-option classes carry
one target-player index; region-change acknowledgement writes its exact fixed i32 body.

## Withheld duplicate/dormant classes

Still intentionally unresolved:

- `rs/o/a/a/a/e` and `V`: duplicate opcode-128 player option 1 serializers;
- `rs/o/a/a/a/f` and `Y`: duplicate opcode-139 player option 4 serializers;
- `rs/o/a/a/a/n`: opcode 41 has dual exact-current semantics (inventory option 2 / equip alias);
- `rs/o/a/a/a/o`: dormant custom opcode 2 serializer;
- `rs/o/a/a/a/p`: dormant custom opcode 6 serializer;
- `rs/o/a/a/a/g`: dormant custom empty opcode 78 serializer;
- `rs/o/a/a/a/x`: dormant custom six-short opcode 109 serializer.

No arbitrary canonical owner is chosen for byte-identical duplicates.

R328 remains non-canonical semantic research only.
