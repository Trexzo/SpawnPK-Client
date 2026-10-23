# Original v311 R94 — recover actual GNU Trove-dependent scene map

**Evidence date:** 2026-10-23. Original owner-private v311 JAR `client(20261021-111920).jar` has SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. **NO original client JAR, recovered private game Java source, game classfiles or extracted vendor binaries are published here.**

## Original dependency resolved with real binary library, NOT a stub

New original `rs/l/e/k.class` — a fixed 74-element scene ID registry and GNU Trove int-to-object maps — was independently recovered as owner-private Java 9 source, then compared against exact original bytecode:

| Original class | Exact original SHA-256 | Independently recompiled, inverse-restored SHA-256 | Original symbolic JVM instructions |
| --- | --- | --- | ---: |
| `rs/l/e/k.class` | `7895bc6ad909f171890eade3f64dccec2fc42b8d629c1a75490ac7fc68aeb852` | `44c3a381bf33864b74e44fd7e785d3a6aca285ef15f7197fd00637d93ca20bfc` | **344/344** |

Full original-name class/member declarations, JVM descriptors, opcode sequence, offsets, branch destinations, symbolic method/field operands and class constant metadata match after normalizing only numeric constant-pool indexes.

**Important change from previous no-game-binary-classpath source islands:** The exact original v311 JAR contains the *real*, obfuscated GNU Trove vendor library: **1,595 `gnu/trove/**/*.class` files**. Java cannot compile ordinary source naming `gnu.trove.f.b.cc` while there is also a `gnu.trove.f` class/interface. A **bounded, disposable compiler-only relocation of seven actual Trove binary classfiles**, `gnu/trove/f/b/cc.class` and its six nested classes, resolves this JVM-to-Java class/package shadow. The rebuilt game Java source temporarily references the relocated, real binary map type; the generated original-game classfile's JVM class/type references are then **restored on copied output** to `gnu/trove/f/b/cc` before exact original symbolic instruction parity and SHA checks.

The vendor compiler JAR is derived **at runtime only** from the exact SHA-pinned owner JAR; its members are verified to be **only `gnu/trove/` vendor classfiles, no `rs/` original game binaries**. It is deleted after the private run, and neither vendor binary nor relocated vendor binary is packaged with the sources. This is not a zero-binary compiler classpath: it is a **genuine, verified third-party vendor-binary-only classpath**. It neither fabricates a Trove type stub nor modifies the original game JAR.

## 66-source compilation and independent behavior

All **65 accepted R93 original-name source classes** and `rs/l/e/k` compile together with one `javac --release 9 -proc:none -g:none` invocation. All **65/65 earlier reconstructed classfile SHA fingerprints remain unchanged**, with **zero source stubs** and **zero missing explicit original `rs/` project dependency references**. The combined **66-source build accounts for 6,794/6,794 matching original symbolic JVM instructions**, 6,450 inherited through identical R93 rebuilt classfile fingerprints and **344 freshly original-vs-rebuilt disassembled**. The existing reviewed temporary `rs/k/c` source alias is separately reversed in copied compiler classfiles, as before.

The new JDK-only isolated original-vs-independent-build behavior probe matched **159/159 cases**: all 74 original scene keys, static map membership for each key, selected absent keys, three separately constructed empty per-instance map fields, and registry size. The 150 R93 behavior cases remain previously certified but were **not rerun** here. This does not establish complete map edge cases, dynamic loading, original full classfile attribute identity, GUI rendering or game/server behavior.

## Clean source archive and deliberately invalid inputs

Owner-only archive: `SpawnPK-v311-R94-Trove-Scene-66-Class-Private-Sources.zip`, SHA-256 **`8145a1edfbae3723884d72dd555283a18d311eee619a747809577c51f3ed23ab`**. It contains exactly 66 private Java sources, pinned previous/current manifests, a standalone vendor-only compiler/JVM verifier, probe and six negative checks. The archive contains **ZERO `.class`, `.jar`, account, asset, credential or font files**.

The ZIP was independently **clean-extracted**. Its full original-source/real-vendor recompilation, exact new JVM parity, 65 prior SHA-preservation checks and 159 real original-vs-rebuilt behavior cases passed. **All six/six clean-extracted negative checks passed**, rejecting (1) tampered source, (2) missing source, (3) wrong original client JAR, (4) changed SHA of a genuine original vendor class, (5) unreviewed vendor compile alias, and (6) altered JVM instructions even after re-pinning both candidate source and compiled-class SHA values.

## Exact distinct-class accounting, limits

Correct prior **R93: 93 distinct original classes / 7,646 original matching JVM instructions across separately accepted builds**. Adding the one verified `rs/l/e/k` / **344 instructions** yields **R94: 94 distinct source-recovered original-v311 classes / 7,990 matching original JVM instructions cumulatively**. **Only 66 classes / 6,794 original instructions compile in this single source island**, NOT all 94 classes together.

The previously unaccepted `rs/l/e/k` now has authentic source and a real verified vendor dependency. Large original `rs/a/a` scene-model and `rs/k/e` renderer source chains are **NOT** thereby recovered, nor are the seven previously provisional `rs/I`/tile source candidates promoted. This milestone also does not prove original complete binary classfile byte identity, runtime native/OpenGL/asset closure, or authentic gameplay.

Public synthetic-only Java9 vendor class/package alias and original-vs-recompiled semantics tests accompany this report; **no original game Java or Trove binary content is in that test**. Public CI can validate the alias principle but cannot repeat the owner-private proof without the owner's original client JAR. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT/UNMERGED**.
