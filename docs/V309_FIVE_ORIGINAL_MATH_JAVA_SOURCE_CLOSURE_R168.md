# R168 — joint original-v309 five-class Java SOURCE build and JVM Code proof

CLIENT-only, stacked on R167 #1058 and source milestone #1004. This is **original first-party Java source recovery**, not the reconstructed server.

## Actual real original client Java recompile

The exact original v309 client JAR SHA is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

Five original-named client JVM math classes have now been independently reconstructed and jointly compiled from Java source in **one Java 9 compilation** with an empty original/external binary classpath:

| Original JVM owner | Method bodies | Matching original JVM instructions |
| --- | ---: | ---: |
| `com/a/b/a/a` — transform | 8 | 401 |
| `com/a/b/a/b` — matrix | 24 | 3,780 |
| `com/a/b/a/c` — quaternion | 11 | 314 |
| `com/a/b/a/d` — angle helper | 6 | 81 |
| `com/a/b/a/e` — vector helper | 5 | 80 |
| **Combined Java source** | **54/54** | **4,656/4,656** |

For each original JVM class, original-vs-rebuilt private javap -p -s -c comparison found identical instruction offsets, JVM opcodes, branch targets and resolved original member/constant operands for every original method. The classfile contents as a whole are **not** byte-identical and do not establish full original StackMap/class attribute identity.

The only sixth Java source needed to compile that bundle is a private **compiler-only stub of original `rs/x/e` Packet** with the required `B():int` and `s():float` method signatures. Its method bodies are explicitly **NOT** verified original behavior, not executed by the proof, and not included in canonical recovered-source/v309/src. No original `rs/x/e.class`, original game JAR, or other project/external binary was used as a javac dependency.

The private exact five-original-Java source ZIP SHA256 is `9d456987cc96b07769e8eb8e13e8c47478a57fbf646b26aed15ddab4b0b3a4fb`. Private compile-only Packet Java ZIP SHA256 is `6fee3e369cc38a5abb30edb6dcb10b9f8a546761708134a102f13dbea720d05e`. These exact files and their raw original-derived Java code stay PRIVATE.

## R168 new GitHub acceptance

The private verifier takes SHA-pinned original v309 JAR, five original-named reconstructed Java sources, and exactly one original-name Java-only Packet type. It demands:

- Exact five original binary owner identities and corresponding SHA-256 class hashes and the original R136 game-linked non-rs matrix exclusion proof.
- Exactly five matching Java sources, no duplicates, and exactly one Packet source owner with an original-JVM-proven class identity; no other `rs/` sources or untrusted binaries allowed.
- Source-only isolated javac --release 9 -g:none -proc:none, empty classpath and sourcepath, and exactly six emitted JVM classfile paths.
- Exact original per-class modifiers, superclass/interfaces, all field name/descriptor/access ABI, every original JVM method identity, **54/54 matching original JVM Code members and 4,656/4,656 instructions**, with JVM max stack/locals, branch operands, exception handlers and same-owner call closure verified by the R150 strict inspector.
- Independent SHA checks before and after recompilation, output only sanitized aggregate proof and digests, no original source emission to GitHub.

Hosted Ubuntu and Windows synthetic CI create **different** example math/source classes and an original game-linked matrix referencing an rs Packet-like class; compile an independent substitute Packet Java source with intentionally different unverified bodies. They verify joint source-only JDK recompile and reject missing original math owner, mutated matrix body, non-original Packet JVM source owner, and SHA drift. R167 quaternion regression also runs.

The exact GitHub R168 CLI needs separate execution on the actual private inputs for an official original-input acceptance result. The independently performed private complete 54-method/4,656-instruction original JVM comparison above is its underlying real evidence; do not misrepresent synthetic CI alone as the original replay.

## Canonical source tree and remaining blocker

The actual PRIVATE recovered-source/v309/src candidate has **1,276 Java files**: the original 1,271 preliminary client Java sources copied unchanged plus the five fully independently reconstructed original math Java classes. None of the unverified helper source stubs is included. Current private source ZIP SHA256: `75a5c61695a6f09179b0cb80738e0e38402b5d74e428618a9ac01165bac6e501`.

Controlled full-input JDK-only javac --release 9 with no original/external classpath reports **2,339 errors**, compared with **2,391** at 1,271 original Java candidates, net **52 fewer**. This is still a failing build, is not directly comparable to earlier provisional-dependency **516** errors, and does not certify whole-client compilation or runtime parity.

**Next primary source target: original rs/x/e Packet implementation and method mapping**, especially the exact `B():int` signed-short reader and `s():float` float reader. The remaining 2,339 diagnostics also include missing third-party libraries and decompiler-generated source defects. Full Java tree and dependency provenance are still incomplete; original source/JAR redistribution needs authorization.
