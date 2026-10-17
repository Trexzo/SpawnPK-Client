# R253 — exact ISAAC Java parity and first real world packet replay

Using canonical R247 reconstructed v309 Java client under Linux Xvfb and the isolated authentic asset staging from R249, recovered session keys from the *source-built* login frame (R252 parser), and implemented standalone server-side ISAAC.

**Independent cipher verification:** 1,024 sequential 32-bit outputs of Python ISAAC exactly matched the real compiled `rs.network.Class257` Java oracle, including cipher block regeneration. The server derives inbound seed as four client key words plus 50.

**Real runtime A (login + 249, 73, 97):** matched localhost login opcode 16 with 106-byte frame; sent response 2,0,0 and correctly ISAAC-framed incoming player identity 249 (3 payload bytes), region 73 (4), and root interface 97 (2). Client logged `[Region] Stand in region: 102800` and `[Regions] Loaded region ID: 103314`, followed by `NullPointerException` while traversing UI children after 97. Thus 97/root ID 548 is **not** a verified safe initialization choice.

**Real runtime B (login + 249, 73 only):** same 106-byte login, correctly framed and sent 249 + 73; client logged both region messages without prior interface NPE and transmitted 56 post-login bytes. Screenshot remained **Loading, please wait**; server shutdown later caused broken-pipe/reconnect. **No stable world/gameplay proof.**

One-step test evidence: `SpawnPK_R253_ISAAC_Real_World_Probe.zip` SHA-256 `b1083557bd6a75871db3567c6fd916433bbc5705839c0457631880f88cb2230c`; includes Python ISAAC implementation, Java oracle source, both localhost probes, redacted second run JSON and loading screenshot. No credentials or login payload persisted and no original client classfiles used at runtime. No production Java modified. Native Windows acceptance unverified.

**Next work:** derive and send a correct minimum player synchronization opcode 81 payload; inspect region map-load dependencies and valid interface root/children before reissuing 97. Keep PR #1084 draft.