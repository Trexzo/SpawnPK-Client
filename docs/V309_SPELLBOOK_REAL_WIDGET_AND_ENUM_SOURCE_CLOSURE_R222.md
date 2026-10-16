# R222 — replace four compiler-only owners with actual readable Java, retaining exact R221 Class179 binary

This is the first class-level source dependency closure step after [R221 #1108](https://github.com/Trexzo/SpawnPK-Client/pull/1108). The R221 single-class source build had eleven compiler-only declaration owners. **Four are now replaced by existing, independently SHA-pinned, real Java source files from the private v309 recovered source tree**, without changing normalized Class179.java.

| Actual readable source | Real Java bytes | SHA256 |
| --- | ---: | --- |
| `rs/interfaces/widgets/Widget.java` | 530 | `b3f77f45537ce65772e066f4bd27b9c3df99ca767479b5704927fb51df60985a` |
| `rs/interfaces/widgets/Class176.java` | 273 | `316e4d1ca79fb0b773c160370c0899c13bc8e1ffe888c6663537cb4f5181bcc2` |
| `rs/interfaces/widgets/Class177.java` | 3,266 | `b9e52f622c580e87a21e8dfecba7aee2e9764bf53341bdc3042c86f9adbdddf6` |
| `rs/interfaces/widgets/Class178.java` | 273 | `ac73c8215e875b5d605ba76920b18c59297197f77eeb5d0dc3cfbad6aaf6be35` |

The authoritative private R203 recovered source ZIP SHA256 is `cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d`. The R220–R221 private evidence ZIP SHA256 is `4e39cdbf11e2ff5191778228a30da0208538f1cae93ff0730ea97dbd3d289658`. Exact original v309 JAR SHA256 is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

## Actual private source-only Java9 replay

A clean temporary build uses **one unmodified source file for each of those four real owners**, plus the exact normalized full `Class179.java` from R221 (SHA256 `e274c0f12c36baeaa129920d5e259897a292b65a1138fc386f1413f00ff60406`). Remaining seven explicitly NONORIGINAL declaration sources are `WidgetComponent`, `HitsplatFont`, `Sprite`, `Class170`, `Launcher`, `Client`, and `Configuration`.

The previous fake `Widget` included 19 static widget builder declarations solely to satisfy the compile experiment. Those declarations are relocated to the **still-fake WidgetComponent source** so the real `Widget.java` is never modified to add a fake implementation. The temporary builder signatures still **do not count as recovered code**.

Using `javac --release 9 -g:none -proc:none -implicit:none`, empty original/external binary classpath and sourcepath, and twelve Java source owners total (the target Class179 + four REAL dependent owners + seven distinct fake support owners), one compile produces exactly twelve classfiles with zero compiler errors.

- Emitted complete `Class179.class`: **17,543 bytes** and SHA256 **`b88820d9893b5a2d5b2ff05f5b88aa6d77dc5ee4a66f377db83758f1590c1c6e`**, *byte-for-byte equal to the R221 semantically verified class*.
- Emitted real `Widget.class`: SHA256 **`80764ebe0d17d04f3b040cf0c0319c5397994fd6ef662cad04647bea752752e6`**, with the original-to-readable R210 Widget class mapping, **6 original method declarations / 11 JVM Code instructions**.
- R221 original `rs/n/c/ap` accepted source-method Code proof remains **14 methods / 4,314 instructions**, with exactly 178 earlier documented `ldc`→`ldc_w` encoding substitutions. This step changed **zero bytes** of the emitted Class179, so there is no new instruction-level drift.
- Compiler-only owners decrease **11 → 7**. This is source-dependency closure under real readable Java; it does **not** reduce the number of files in the pinned full private client tree, nor demonstrate a full-client source build.

## Reproducibility and boundaries

The R222 public verifier takes all three SHA-pinned private artifacts, uses AST **literal-only** parsing of the R221 template's 11 fake helper Java strings (never executes private Python script), replaces the four declared real sources from R203, and compiles the complete Class179 + Widget + enums together. It compares the resulting Class179 byte-for-byte to R221's pinned accepted class; separately checks the readable Widget JVM Code against the original pinned `rs/n/c.class`; and replays the R221 all-14-method original Code verifier.

No proprietary source/JAR or fake game implementation enters GitHub. Hosted Ubuntu and Windows tests compile unrelated invented Java with four actual-in-fixture source replacements, reject injected template expressions, missing/changed owners and altered source fingerprints, and check the earlier R221 comparator. A hosted synthetic pass alone does not replay original private inputs.

**Remaining:** Seven temporary nonoriginal dependencies, entire-v309 source tree compiler success, original runtime/behavior, classfile byte identity to original obfuscated `rs/n/c/ap`, and redistribution rights. Do not claim those as complete. The last comparable full-client JDK-only source frontier remains **1,295 Java files / 2,358 errors**. Next investigate independently recovered actual `WidgetComponent` and `Sprite` readable Java and their dependency closure, rather than adding new stub behavior.

PR stack: R220 [#1107](https://github.com/Trexzo/SpawnPK-Client/pull/1107) → R221 [#1108](https://github.com/Trexzo/SpawnPK-Client/pull/1108) → R222. Keep draft while full dependency and runtime acceptance remain open.
