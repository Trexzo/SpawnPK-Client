# R250 — client-derived first-world packet contract (read-only)

Independent audit of canonical private R247 Java sources (same source base used for R249 graphical test), without introducing or modifying production code.

Actual source file SHA256:
- `rs/Client.java`: `13a7c5a386112c9ca122fd8557dfca0a77e024de8e29a203d205528b1e88fc9d`
- `rs/io/IncomingPacketLengths.java`: `841430ca2f80291d26740544027f41c557a081b22c230c920004480c282bcb14`

Executed `python tools/r250_world_packet_contract.py <private_source_root>`: 12 structural/length assertions PASS.

## Concrete client dispatch
- Post-login opcode read: `raw_byte - incomingCipher.method0() & 255`. ISAAC is configured from client session seed + 50 in login code. **Raw packet opcode bytes are invalid** after success unless corresponding cipher state is used.
- Frame sizes from `IncomingPacketLengths.incomingLengths`: fixed nonnegative count; `-1` 8-bit size; `-2` 16-bit size.
- `73`: normal region, fixed 4 bytes. The handler reads coordinates with `method761()` and `method3348()` and sets `baseX=(field856-6)*8`, `baseY=(field857-6)*8`; cache map requests may follow.
- `241`: constructed region, `-2`; bitstream zone template processing.
- `81`: player synchronization, `-2`.
- `65`: NPC synchronization, `-2`.
- `249`: player identity/membership-style fields, fixed 3 bytes; exact byte-endianness must be proven from Packet implementation before transmitting.
- `97`: root interface, fixed 2 bytes.
- `176`: post-login account info, fixed 10 bytes.
- `185`: *incoming* opcode 185 has fixed 2 bytes; do not confuse with outgoing widget-click opcode 185.

## Important gates
R249 established real client's R247 source-built login-success response 2 triggers “Loading, please wait”, not a stable world. R250 does not emit server world packets or assert success. Next implement **a controlled local emulator** with matching ISAAC and verified Packet reader semantics, then test minimum region, identity, player sync and interface frame against the R247 client; prove visible stable game frame and continued loopback after first tick. Do not guess payload layouts from packet names. No original .class client fallback, live-network login or asset modifications.

No new native Windows evidence. Keep PR #1084 draft.