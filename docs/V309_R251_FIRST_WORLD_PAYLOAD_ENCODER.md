# R251 — first-world payload codec, private test evidence

Read-only audit of canonical R247 `Client.java` and `Packet.java` confirms three inbound packet encodings:

- Opcode 73, fixed 4 bytes: region x read by `method761()` (big-endian, low byte minus 128), region y `method3348()` (big-endian unsigned short).
- Opcode 249, fixed 3 bytes: flag read by `method2188()` (byte minus 128), player index `method1836()` (transformed low byte minus 128, then high byte).
- Opcode 97, fixed 2 bytes: root interface ID read by `method3348()` (big-endian unsigned short).

Private `world_packet_codec.py` and `test_world_packet_codec.py` executed six passing Python tests, including value-boundary roundtrips and rejecting raw opcode output when ISAAC cipher state is absent. SHA256 of combined private proof ZIP `cec74d2cce7e8db228e6134e6d9e796e1dc4b0979b34284c3cdc97d8b66d5d24`.

**Gating finding:** R249 dummy listener receives an RSA-encrypted login block but does not decrypt its session ISAAC seeds. Packet bytes must use a matching server cipher; these payload encoders alone cannot establish a real world session. R251 has not transmitted a world packet to the source-built client, has not reached gameplay, and has not tested Windows. No production Java changed; #1084 stays draft.
