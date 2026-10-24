# Original v311 R101 — SHA-pinned Google shader include processor recovery

**Private verification date:** 2026-10-23. Owner-supplied original `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Original game JAR, private reconstructed Java, compiled game classfiles, and source/JVM probes are **not uploaded to public GitHub**.

## One genuinely new original renderer dependency

| Original JVM class | Original SHA-256 | Independent rebuilt/inverse-restored SHA-256 | Exact original JVM instructions |
| --- | --- | --- | ---: |
| `rs/k/d/a.class` — shader `#include` preprocessor | `04f8c5b6659d21ccc66d28c9540e5bcc7961e9387c7e57d363c7fa1a2ce2f482` | `6442e2dfcc774d6c1043fd26a2a16400332984fbf054ebd21c3bfdc142ff5483` | **142/142** |

Original JVM declarations, fields, method descriptors, ordered instructions, offsets, branches and exception handlers match the independently Java9-source-compiled output, normalizing only numeric constant-pool indexes. The original `LambdaMetafactory` bootstrap handle directly targets `rs/k/d/a.a:(Class,String)String`; rebuilt bootstrap metadata is also verified to match, with no extra compiler forwarding method remaining. Complete original classfile byte identity, original authored source text, full attribute identity and full graphics/runtime behavior are **not** claimed.

## Authentic vendor binary dependency and reversible compiler-only repairs

Exactly **2,607 original `com/google/` vendor classes** and **1,595 original `gnu/trove/` vendor classes** are extracted transiently from the exact SHA-pinned owner original JAR. The compiler classpath contains **only these real third-party classes and ZERO original `rs/` game classes**, and the private source build contains zero implementation stubs.

The original Google class `com/google/a/j/v.class` (original SHA256 `a69de802601edf5a8ef3893046093ea95c4f1a4a645f91ac2a155fa31b281a91`) has had its checked `IOException` method `Exceptions` metadata stripped by obfuscation. This prevents `javac` from compiling the original `rs/k/d/a` source's real `catch(IOException)`. A narrowly scoped **compile-only method Exceptions attribute restoration on a copied genuine vendor classfile** corrects that; no vendor executable `Code` changes. The runtime behavior comparison uses the **unmodified original Google vendor binaries**, not the compile-only copy.

The existing original `rs/k/d.class` JVM type clashes with the Java package of `rs/k/d/a`. A disposable, reviewed owner-type name alias enables compiling both original-source Java types, followed by inverse-JVM-name restoration on copies. Java9 `javac` also synthesizes an extra lambda forwarder; the private, SHA-pinned inverse-restoration removes exactly that redundant forwarding method, fixes the associated bootstrap method-handle reference to the original `a(Class,String)` target and restores the original target method synthetic flag. Executable JVM `Code` and original exception-handler tables of retained methods are not edited. A strict actual original-vs-rebuilt 142-instruction and bootstrap comparison follows every restoration.

## 73-class source-generated build and original-vs-rebuilt behavior

The existing R100 source island has 71 independently recovered Java source types plus one compiler-generated switch-table donor. R101 adds one genuine original shader preprocessor source type, giving **72 genuine original Java source declarations plus the one accepted switch-table donor**. One Java9 compiler invocation produces **73 original-named classfiles / 7,331 original matching JVM instructions accounted for**. **All 72 previous R100 rebuilt class SHA-256 fingerprints are unchanged**, retaining the prior certified 7,189 instruction matches; **142 new** instructions are freshly original-vs-rebuilt disassembled. The generated class set is exact, the original constant-pool project dependency closure has no missing `rs/` types, and there are zero Java source stubs.

An isolated Java reflection probe (compiled without original-game types) executed independently against the complete original JAR and the rebuilt classfiles with genuine unmodified vendor binaries. **23/23 new behavior cases match**, covering line splitting, CR/LF, `#include` expansion, recursive replacements, missing includes, resolver precedence, UTF-8 classpath resources, IOException wrapping, null input and reflection member shape. The previous R100 behavior cases were **not** rerun.

## Independent clean extraction and refusal tests

The owner-private ZIP `SpawnPK-v311-R101-Shader-Include-73-Class-Private-Sources.zip` has SHA256 **`831e6c01410dca3298a07941af8cba52eb4d5ba6d32dbd7e2f1d6684ac352d96`**, 144,574 bytes. It includes exactly **73 canonical reconstructed Java source files** plus four Java probe files, original/source/rebuilt SHA manifests, a source compiler/verifier, strict metadata restoration scripts, isolated behavior fixtures and deliberate failure tests. It contains **no original JAR, any compiled `.class`/`.jar` binaries, private vendor files, game assets, fonts, account data or credentials**.

The ZIP was freshly extracted; its 73-class original/source/rebuilt hash, compiler, dependency closure, new symbolic JVM parity/bootstrap and 23-case behavior verifier all passed. **Eight/eight deliberately invalid cases passed** (all fail closed): modified source, missing source, wrong whole original JAR, forged authentic Google vendor SHA, unauthorized class/package alias, modified Google compile-only metadata restoration tool, modified direct-lambda restorer, and modified source-generated JVM instructions **even after source and rebuilt SHA fingerprints were both repinned**.

## Audited distinct totals, public synthetic coverage and blockers

R100 accepted **100 distinct recovered original-v311 classes / 8,385 original JVM instruction matches** across separately verified source-build records. Adding one genuinely new class and 142 exact original JVM instruction matches yields **R101: 101 distinct accepted classes / 8,527 original matching instructions cumulatively**, **not** a 101-class compilation. The largest combined source-generated closed output is **73 original classfiles / 7,331 instructions**, with a genuine vendor-only binary compiler classpath and original game binary exclusion.

Hosted CI can run independent *synthetic-only toy Java9 vendor checked-exception metadata regressions*, but it has no access to the owner's real client or reconstructed game Java and cannot certify this private original-JAR result.

The original `rs/k/e` renderer, `rs/a/a` scene model and seven previously provisional `rs/I`/tile original classes remain unrecovered. No complete original source tree, runtime OpenGL/native/asset closure, whole-client startup or authenticated gameplay acceptance is claimed. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**.
