# Chat 2 — residual exact outgoing packets R327

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/o/a/a/a/I` -> `CLIENT_CLASS_000721` -> `DialogueContinuePacket`
- `rs/o/a/a/a/S` -> `CLIENT_CLASS_000731` -> `GroundItemOption3Packet`
- review: `SEMREVIEW_261BB90BD3A8726EA321`

## Dialogue continuation

The generated packet writes opcode 40 plus one widget ID.

Exact-current dialogue lifecycle independently fixes C2S40 as the Continue response paired
with open chatbox state.

## Ground-item option 3

The generated packet writes opcode 236 plus three fields matching itemId/worldX/worldY.

Exact-current action routing fixes opcode 236 as ground-item option 3.

The name intentionally remains option-based. The client inserts `Take` as the default
third ground action when the definition does not provide one, but exact-current item
definitions can populate that slot with other verbs.

## Boundary

Other residual generated packet opcodes remain unnamed unless their exact-current transport
contract is independently fixed. R327 is non-canonical semantic research only.
