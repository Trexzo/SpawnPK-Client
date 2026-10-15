# R166 — original v309 12-component transform Java class fully reconstructed

Client-only source recovery, stacked on R165 #1056 and tracked by original-source milestone #1004. Original user JAR and recovered Java remain private.

## Independent actual-original-v309 recompilation

SHA-pinned original class: `com/a/b/a/a.class` **1,850 bytes**, SHA256 `6b4119f5c96d9ac6d2a2ecd3b0ead16c09539e919df47266820ac3020bbfb709`. It declares **12 instance float fields, one static final original transform instance, and eight JVM methods**.

From the actual original v309 JVM operations, an independently generated original-named Java9 source class preserves float-local values, Math.cos/sin float–double casts, original field assignment ordering and precision, a three-float translation update, 12-float formatted matrix output and the static singleton initializer. Real Java9 `javac --release 9 -g:none -proc:none -implicit:none` compiled with **NO original client or external classpath**, yielding **401/401 matching original JVM instructions and offsets**, including all resolved field/method references:

| Original method | Matching original instructions |
| --- | ---: |
| Constructor | 5 |
| Identity reset | 37 |
| Three original float rotation routines | 103 each (309) |
| Three-float translation | 19 |
| 12-component toString formatting | 26 |
| Static initializer | 5 |
| **Total all 8 methods** | **401** |

Verified private input/original output pins:
- Original full v309 client JAR SHA256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`
- Original transform class SHA256: `6b4119f5c96d9ac6d2a2ecd3b0ead16c09539e919df47266820ac3020bbfb709`
- Private recovered transform Java source-file SHA256: `ac3b82d52f04a82c7487105e703e18acf62fffee61e56b780b6bd3f22d002c24`
- Private isolated recompiled class SHA256: `48081faa813e01b325957c25a36f228958c54aa692a20f439ff4a7bcbda28648`
- Private previous 1,274-Java tree ZIP SHA256: `e9f641417e95de3c25c6534dff199e8d2d8a47f92d5250c40a0158a32ca588f6`
- New private **1,275-Java** tree ZIP SHA256: `60e18b49e671545f993b326398cb6654f80cbd0ac36d2c2b07877ad056387e7f`

The class is reconstructed with all original JVM Code, but the compiled full `.class` file hash differs, so do not infer byte-identical classfile metadata, automatic runtime parity or source redistribution authorization.

## Actual whole-source JDK-only javac delta

Original all-Java-input compilation with JDK21 `javac --release 9 -proc:none -implicit:none -Xmaxerrs 10000`, empty original/external classpath, each candidate compiled with the same options:

| Stage | Java files | Errors |
| --- | ---: | ---: |
| Original source candidates | 1,271 | 2,391 |
| + full matrix | 1,272 | 2,364 |
| + full vector | 1,273 | 2,358 |
| + angle utility | 1,274 | 2,355 |
| + original transform | **1,275** | **2,353** |

This stage removes **two further JDK-only compiler errors**, 38 fewer since original baseline. It is not a complete client build and not directly comparable to the earlier 516 errors from a different classpath/collision-normalized diagnostic setup.

## GitHub implementation and next work

R166 adds a pinned original class-vs-Java-source verifier built atop R164's full field/method/Code original parity. It explicitly checks the original JVM class modifier flags, superclass and interfaces, as well as the `StringConcatFactory` bootstrap recipe for 12-float formatting. The recipe matters because changing separator strings can preserve the 26 source method instructions while changing displayed output.

R166's private verification must pass BEFORE inserting exactly this one full original transform Java source under `recovered-source/v309/src/`, without overwriting any of the previous 1,274 files or inserting placeholder Packet/math sources.

Synthetic Ubuntu/Windows tests compile a different independent 12-float transform Java class, then verify eight source methods and 13 fields and reject altered float arithmetic, altered class modifiers, changed string concatenation recipe, changed SHA or unsafe overlay. No private original Java/JAR enters public GitHub Actions.

The original quaternion `com/a/b/a/c` and original Packet `rs/x/e` still require complete independent source recovery. The original-source candidate remains private, and the full v309 client still fails javac due to 2,353 outstanding JDK-only diagnostics. StackMap/classfile metadata, helper runtime parity and third-party provenance remain separate.
