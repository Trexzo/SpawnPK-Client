# R223 — five more genuine v309 decompiled source owners compile together

The previous [R222 #1109](https://github.com/Trexzo/SpawnPK-Client/pull/1109) build compiled complete original-semantic readable `Class179.java` with four genuine dependencies and seven temporary Java declarations. R223 expands that same experiment by integrating **five additional exact existing real readable Java files**, sourced byte-for-byte unchanged from the SHA-pinned R203 experimental v309 source tree.

## New genuine Java sources, not invented behaviors

| Real source file | Bytes | SHA-256 |
| --- | ---: | --- |
| `rs/interfaces/widgets/Class170.java` | 9,043 | `73a2f01084e9abd1c86c9d6cad95cb35ce58873f0f45a771b79c36e2bad54b42` |
| `rs/interfaces/widgets/Class168.java` | 331 | `28a814fd331abe90eb2711929d4edc84c184d7a41bc8fcf90b13117b5ec20103` |
| `rs/interfaces/widgets/Class169.java` | 1,456 | `591e74de23e0824070636a8ff4a5197e347e5b495f2fe2698b880f05b664d996` |
| `rs/graphics/hud/Class69.java` | 236 | `fdcbbc45cdb74b792037b9ca93019ebc8ab21e929ce1f21391d717a409396cde` |
| `rs/pkg39/Class53.java` | 471 | `22126d408186bd402e87619d4774daffde2b2955dead0ec73bd44abc9bdc4596` |

These build alongside the four R222 genuine readable sources `Widget.java`, `Class176.java`, `Class177.java`, `Class178.java`, and the full normalized `Class179.java`. They are existing readable original-decompiled source candidates, not automatically accepted bytecode-identical originals.

The exact private sources/JAR/evidence inputs remain:
- Original v309 client JAR SHA `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.
- R203 private source tree ZIP SHA `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`.
- R220–R221 private unified evidence ZIP SHA `4e39cdbf11e2ff5191778228a30da0208538f1cae93ff0730ea97dbd3d289658`.

## Isolated multi-source Java 9 build — passed

The isolated JDK21 compiler, using `--release 9 -g:none -proc:none -implicit:none` and an EMPTY original/external classpath and sourcepath, compiled **18 Java source owners** in one invocation:

- **10 genuine candidate source owners:** nine genuine dependency files plus the complete normalized `Class179.java`.
- **8 temporary NONORIGINAL declaration owners:** `WidgetComponent`, `HitsplatFont`, `Sprite`, `Launcher`, `Client`, `Configuration`, plus new `Class260` and `Overlay` interfaces/signatures.

R222 had seven fake declarations, of which `Class170` is now replaced by genuine Java. R223 adds two new nonoriginal signatures required by genuine `Class168` and `Class169`, leaving **eight temporary declarations in total**, not six and not zero. The four new inherited UI factory signatures are attached ONLY to the still-fake `WidgetComponent` source, never to the independently original-evidenced genuine `Widget.java`.

Local complete-source experiment: **zero javac errors and exactly 18 classfiles**, no game classes executed.

| Compiled owner | Resulting classfile SHA256 | Acceptance |
| --- | --- | --- |
| Complete `Class179.class` | `b88820d9893b5a2d5b2ff05f5b88aa6d77dc5ee4a66f377db83758f1590c1c6e` | **Byte-for-byte unchanged from original-semantic R221/R222 built class** |
| `Widget.class` | `80764ebe0d17d04f3b040cf0c0319c5397994fd6ef662cad04647bea752752e6` | Byte-identical to R222's independently 11-original-JVM-instruction-verified candidate |
| `Class170.class` | `f7ac42cca5d8c44aa827edaf947b1698724d4151a84a4fef9ee2a5097469f917` | Genuine readable source compilation; separate original-JVM parity **not verified** |
| `Class168.class` | `0604158afc9475bdae752a0e2df7fd64483b2208dd7c571f709239416779db02` | Genuine readable source compilation; separate original-JVM parity **not verified** |
| `Class169.class` | `0f3f82bb7ffb5f4c91c67798e54851e989d32356d5f8dfa55a88d5725d9fe776` | Genuine readable source compilation; separate original-JVM parity **not verified** |

Since complete compiled `Class179.class` remains **byte-for-byte identical to the class previously matched to the pinned original v309 `rs/n/c/ap`**, R221's complete **14 methods / 4,314 original-equivalent JVM instructions** remain unchanged. No client code executed, so this is source compilation and classfile verification, not an end-to-end gameplay test.

## Public verifier and next dependencies

The public R223 verifier requires all three SHA-pinned private inputs, uses **literal-only AST** decoding of R221's temporary signature template (never executes a private script), verifies all actual real source hashes, permits **only** strict changes to explicitly temporary API declaration sources, compiles all 18 Java classes in one isolated Java 9 build, and replays the original `Widget` and `Class179` proofs. It refuses unexpected extra classfiles or any changed original-verified output hash.

Hosted GitHub Actions uses unrelated invented Java code with the same 18-owner structural constraints on Ubuntu and Windows. The genuine game source/JAR are **not** distributed in public CI.

**Still missing:** eight compiler-only declarations, complete original-JVM method-by-method acceptance of these newly integrated dependent sources, real transitive dependency closure, whole-client source compilation, runtime, original obfuscated classfile byte identity and redistribution rights. The last comparable full-source JDK-only client baseline remains **1,295 Java files and 2,358 compiler errors**. Keep PR draft.

Next targeted closure: `Class260` and `Overlay` transitive dependencies or the actual `HitsplatFont`/rasterization source family, grounded in an original-vs-readable ABI inventory.
