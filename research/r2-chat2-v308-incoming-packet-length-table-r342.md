# Chat 2 — exact-v308 incoming packet length table R342

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/f/d` -> `CLIENT_CLASS_000174` -> `IncomingPacketLengthTable`
- proposal: `SEMPROP_422AA50CC272C78998B9`
- review: `SEMREVIEW_C5FE746BAEB734E8B9D0`

## Exact Client framing path

After Client reads the next inbound opcode byte and applies the live ISAAC cipher state, it
stores the decoded opcode and immediately performs:

`packetLength = rs/f/d.b[opcode]`

The following branches prove the length-table semantics:

- `-1` -> read one unsigned byte for the actual packet length;
- `-2` -> read two bytes / unsigned short for the actual packet length;
- non-negative value -> fixed packet length.

Client then waits until that many bytes are available before reading the packet body.

## Reference boundary

The only exact-v308 external reference to `rs/f/d` is this Client inbound framing path.

The class also contains a second static int array, but stock v308 has no external reference
to it. R342 therefore names the live class by the proven incoming-length role and makes no
claim for that unused companion array.

R342 remains non-canonical semantic research only.
