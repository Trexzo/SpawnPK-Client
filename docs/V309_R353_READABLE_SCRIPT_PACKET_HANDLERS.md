# R353 — readable v309 script-packet handlers (source pass 2)

**Correct repository:** `Trexzo/SpawnPK-Client`. The **complete 1,277-source R315** candidate is already independently clean-buildable; this increment makes a bounded portion of that tree readable. It is private Java source research, **not** an original-author name restoration or original-v309 executable-JAR parity acceptance.

## Three names grounded in recovered source and dispatch registry

The SHA-verified R315 source contains an `AbstractScriptPacketHandler` base, dispatch registration in `rs/scriptpacket/ScriptPacketRegistry.java`, and specific handler implementations:

| Original class | Readable inferred name | Registered script opcode | Code evidence |
| --- | --- | ---: | --- |
| `rs.scriptpacket.handler.Class261` | `ClientStateScriptPacketHandler` | 32 | Reads a subtype, updates client integer state, spell UI widgets, amount input prompt and overlay settings |
| `rs.scriptpacket.handler.Class262` | `NpcStateResetScriptPacketHandler` | 21 | Reads NPC index from packet, checks `client.npcs` bounds and clears an NPC-owned collection |
| `rs.scriptpacket.handler.Class263` | `GrandExchangeScriptPacketHandler` | 14 | Decodes 26 subcommands, updates `GrandExchangeWidget`, widget texts, item slots and layout |

These are **inferred and reviewable names**. The private rename changes the corresponding Java owner filenames and all source references, including registration dispatch and the `UiPacketDecoder` source comment. It does not rename internal method/field symbols, modify protocol numeric IDs, or alter original JARs.

### Measured real private R315 pass2

Input: full R315 candidate after Source Pass 1 (`AbstractScriptPacketHandler`), **1,277 Java files**.

- `Class261`: 3 identifier occurrences / 2 files
- `Class262`: 3 identifier occurrences / 2 files
- `Class263`: 5 identifier occurrences / 3 files (includes one source diagnostic comment)
- **11** identifier replacements across **5 unique Java files** (registry + three owners + one source diagnostic); three source filenames change.
- Inverse names and filenames reconstruct **all 1,277 Java files from R352 byte-for-byte**, zero source drift outside mapped identifiers.
- Real private source-only compile: **JDK21 `javac --release 11 -proc:none -g:none` exit 0**; **1,386 compiled classfiles**.
- Two private dependency JARs contain no `rs/` classes; therefore this full-source build does **not** rely on original-game project binary fallback.
- Compiled private renamed JAR SHA-256: `d3c86c83393b219aa2ac6c4134194764c9836df388af6e5970c21349c1342c13`. This hash is a deterministic *candidate build* identifier, **not** an untouched-original-v309 bytecode equivalence verdict.
- Full private source ZIP: `SpawnPK-v309-R315-Readable-Deobf-Pass2-Source.zip`, SHA-256 `3d9daeb81c1367edc7a2e843a71638d22835bd485bc2d4c09eb0aa43d01b5f22`. Its manifest includes per-handler opcode and actual source SHA changes.

### GitHub reproducibility

`scripts/prepare_v309_r353_scriptpacket_names.py` accepts only a verified R352 private source stage. It confirms the original R315 archive pin, 1,277 individual input SHA-256 values, the three owner class shapes, the three exact registry opcodes and the witnessed file/reference counts. It generates a **new, private** renamed tree and per-file SHA manifest and reverses all edits in memory to prove exact input restoration.

```powershell
py -3 scripts/prepare_v309_r353_scriptpacket_names.py `
  --r352-private-stage "C:\private\v309-r352-readable-source" `
  --new-private-output "C:\private\v309-r353-readable-scriptpacket"
```

Hosted Windows/Linux CI uses **synthetic source fixtures only**, testing wrong registry opcode, unrelated namespace reference, altered implementation shape, invalid SHA/provenance, reused destination, and the inverse transform. It does not carry original client Java/JAR or private dependencies.

### Remaining source deobfuscation work

Source Pass 1 removed `Class260`; this pass removes `Class261`, `Class262` and `Class263`. The formerly reported **306 numeric `Class<number>.java` filenames are now 303**. Most `field<number>` and `method<number>` names remain. Only rename when grounded in source usage, registry/method evidence and full-source compile; then independently evaluate JVM symbolic equivalence and reflection-sensitive references before any future Source-M1 publication.

**Production v312, updater, original v309 JAR, runtime caches, account/server and public main branch remain unchanged. Keep draft/unmerged.**
