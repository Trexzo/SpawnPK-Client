# R324 — server-side inventory ordering veto tested with authentic v309 client

28 October 2026. Redacted results of an owner-private local test using the unchanged **1,277-source-built v309 client** JAR (1,386 classfiles; SHA-256 `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`) and authentic 10,772-file cache.

R323 demonstrated that a stale incoming full-inventory opcode **53** can visibly overwrite the current client inventory. Since opcode53 has no epoch/revision field, this old client cannot detect a stale snapshot on its own.

**R324 instead guards the synthetic server's outgoing stream.** After restoring persistent epoch1 (Logs x1, slot0; Coins x7, slot1), the test submits outdated epoch0 inventory work before a current epoch1 snapshot and again as a late retry. The reference local-server outbox rejects both epoch0 snapshots and sends only the current revision. Actual socket-send ledger: exactly **two inventory opcode53 frames total**—the initial restored inventory and one current-epoch resend; **zero stale inventory frames**.

The real original-client GUI item rectangle (683,382–792,441) remained unchanged after both the proposed stale batch and the late retry (**0 changed pixels, twice**). The authoritative synthetic-server state SHA-256 remained `d0240cfd5d72dc44f3206a16156335a91fa38f6ed78569a5c1f33b1d812c1a48`.

A first real GUI replay passed at **22.16 seconds**; a stricter independent second replay exited **0 at 21.75 seconds**, recorded an explicit socket-send receipt, and cleanly terminated the client/server. That receipt (SHA-256 `2511b5e9c7281d76be73386d98eda9d978fffa0a6e0caf58e9b8c63120e6b24a`) confirms both rejected stale proposals and the two outgoing inventory frames.

**GitHub:** private [draft PR #4](https://github.com/Trexzo/fullspkclient-private/pull/4) contains the original-independent `recovery/v309-r324` ordered-outbox reference, SHA-pinned isolated GUI fixture generator, genuine screenshot/socket-ledger verifier, and negative/positive tests in Windows/Linux CI. Private ZIP `SpawnPK-v309-R324-Private-Ordered-Inventory-Acceptance.zip`, **678,297 bytes**, SHA-256 `6a5f6265f373fa90080ca75f061f32023c6cf46290dc9cffacc5dbc7f6d71a29`, contains sanitized actual-client evidence and passed a clean-extraction independent verifier plus **18 source-only tests**.

**Limitations:** The R324 gate is an **undeployed reference implementation in a synthetic local server**; it cannot recall an old packet already written to the socket, and it is not proof of the production SpawnPK server's database, concurrency, persistence or ordering behavior. No production client changes, real accounts, authenticated public-server gameplay, native Windows GPU or original-v311 bytecode parity certified.

**The complete private 1,277 recovered Java files and three pinned JARs are still NOT on GitHub**, tracked at [private issue #3](https://github.com/Trexzo/fullspkclient-private/issues/3). Keep public PR #1143 and private PR #4 draft/unmerged, preserve owner main and separate v311 recovery.
