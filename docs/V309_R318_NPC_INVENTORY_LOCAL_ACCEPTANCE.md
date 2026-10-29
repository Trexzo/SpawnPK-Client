# R318 — original-source client NPC and inventory acceptance (27 October 2026)

Real owner-cache-backed v309 local graphical replay, without modifying the production R311 class-only JAR. The isolated synthetic ISAAC localhost server sent opcode **65** (NPC slot **47**, definition 1) and opcode **53** (inventory widget **3214**, first item ID **996**, quantity **7**). A private diagnostic-only Client.java overlay confirmed both were applied to real client state. The authentic NPC appeared as **Man (level 2)** in the rendered world.

An actual Java Robot right-click selected **Talk-to Man** from the in-game context menu. The client emitted ISAAC-decoded opcode **155** for NPC slot 47; the local server sent response opcode **253**. Diagnostic GUI run **PASS 22.64s**, authentic 46-byte outgoing client wire SHA-256 `31d36b319b07a657acbf148f9604e5ec37b22812a5907b3adf9a57c43f30a1c5`.

A second independent isolated GUI replay ran **only the unchanged compiled production JAR** (no instrumented Client.class) and completed the same NPC Talk-to exchange, **PASS 22.66s**; separate authentic 46-byte ISAAC client wire SHA-256 `71021f1436474189e0e0b98afc6794a6fec485680ad080deb36635ba566b0641`.

Unchanged compiled client JAR SHA-256 `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`. **Zero production Java changes**. First failed click targeted the NPC **Attack** action (y349) and was correctly refused as a Talk-to acceptance result; the corrected GUI click chose **Talk-to** (y365).

All fixture generation, private-source SHA gating, real-receipt validation and ten synthetic negative/positive tests are committed to [PRIVATE PR #4](https://github.com/Trexzo/fullspkclient-private/pull/4), under `recovery/v309-r318/`. The complete 1,277 Java source GitHub import remains outstanding in [private issue #3](https://github.com/Trexzo/fullspkclient-private/issues/3); there is no claim it has been uploaded.

**Explicit boundaries:** local synthetic server only, not actual production login or dialogue systems. Inventory update was observed in original client widget data, **not proven visible in currently active inventory UI**. No native Windows GPU or multihour NPC/inventory operation tested. The diagnostic overlay must never be used in production. Keep draft PR unmerged; separate original v311 recovery unchanged.
