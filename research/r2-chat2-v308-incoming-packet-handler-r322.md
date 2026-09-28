# Chat 2 — exact-v308 outgoing packet contract R322

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected result

- `rs/o/a/a/a` -> `CLIENT_CLASS_000686` -> `OutgoingPacket`
- proposal: `SEMPROP_2C9876842D87391F87A2`
- review: `SEMREVIEW_3A168E8B75A5E913F491`

The first R322 attempt called this interface `IncomingPacketHandler`. That interpretation
was rejected after direct inspection of the concrete family.

## Exact contract

The interface exposes one method:

`void a(rs.x.e)`

R29 already identifies `rs/x/e` as `Stream`.

## Direction proof

Exact v308 contains **52** concrete implementations under:

`rs/o/a/a/a/*`

Every inspected implementation serializes a packet, rather than reading one.

The method pattern is:

1. write one fixed packet opcode with `Stream.a(int)`;
2. write zero or more constructor-held payload fields through Stream write transforms;
3. return.

Examples include fixed outgoing opcodes:

- 188
- 133
- 72
- 202
- 210

Concrete classes are packet-shaped value objects. Some hold one long/int; others hold
multiple primitive payload values; zero-payload packets simply write their fixed opcode.

## Client send path

`Client.a(rs.o.a.a.a)` passes the shared output Stream `Client.fv` to the packet.

After serialization, the same path sends the resulting stream length/byte array through
the active connection writer and resets stream bookkeeping. IOException/connection failures
are handled as send-path failures.

This proves the family is client-to-server ordinary packet serialization.

## Boundary

R115 `ScriptPacketHandler` is unrelated: it decodes the opcode-250 server ScriptPacket
subprotocol.

R322 intentionally names only the base outgoing-packet contract. The 52 concrete packet
classes remain future semantic recovery targets and should be named from their exact opcode
and payload/call-site behavior.

R322 remains non-canonical semantic research only.
