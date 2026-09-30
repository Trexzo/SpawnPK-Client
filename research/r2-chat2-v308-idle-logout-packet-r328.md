# Chat 2 continuation — exact-v308 idle logout packet R328

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/o/a/a/a/U`
- stable ID: `CLIENT_CLASS_000733`
- semantic: `IdleLogoutPacket`
- proposal: `SEMPROP_D546F33CAE130921A764`
- review: `SEMREVIEW_52719EBCA1012AFB1E63`

## Exact packet shape

The class implements the corrected R322 `OutgoingPacket` contract.

Its serializer writes:

- opcode **202**
- no payload

## Runtime corroboration

A LocalLab run previously remained healthy until the client emitted opcode 202 after an
idle period. The decoder did not know its framing, entered the fail-closed paused state,
and subsequent movement/input packets were no longer decoded even though rendering,
TCP and the world scheduler remained alive.

The recovered contract is:

`C2S202 -> FIXED0 -> IDLE_LOGOUT`

Adding that framing is what prevented the half-responsive idle-session failure.

## Boundary

The name is specifically `IdleLogoutPacket`.

No claim is made that opcode 202 is the explicit user-selected logout route. The generated
opcode-109 packet remains unresolved because no exact-current C2S semantic authority has
yet joined it.

R328 remains non-canonical semantic research only.
