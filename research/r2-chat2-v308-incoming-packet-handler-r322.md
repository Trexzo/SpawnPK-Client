# Chat 2 — exact-v308 incoming packet handler contract R322

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/o/a/a/a` -> `CLIENT_CLASS_000686` -> `IncomingPacketHandler`
- proposal: `SEMPROP_18FD8C7C3CEE516BCBD7`
- review: `SEMREVIEW_E3F62D5DA27AC6E49CA4`

## Exact contract

The interface has one method only:

`void a(rs.x.e)`

R29 already identifies `rs/x/e` as `Stream`.

## Exact Client dispatch

Client contains a direct helper accepting this interface. In the active connected/session
state it invokes the handler with the live incoming packet Stream `Client.fv`.

Immediately after handler execution the same Client path performs incoming-buffer
bookkeeping and packet-dispatch exception handling.

This is therefore the ordinary incoming/server packet handler contract, not a generic
Stream consumer.

## Concrete family

Exact v308 contains 52 concrete classes under:

`rs/o/a/a/a/*`

that implement/reference this base interface. The stable class sequence is contiguous:

- `rs/o` is already R52 `CLIENT_CLASS_000685`
- base handler is `CLIENT_CLASS_000686`
- concrete packet-handler family occupies the following IDs through `000738`
- `rs/p` begins at `CLIENT_CLASS_000739`

## Boundary

This is distinct from R115 `ScriptPacketHandler`, which is the opcode-250 ScriptPacket
subprotocol.

R322 intentionally names only the base contract. Concrete incoming packet handlers should
be recovered individually from their exact decode/mutation semantics.

R322 remains non-canonical semantic research only.
