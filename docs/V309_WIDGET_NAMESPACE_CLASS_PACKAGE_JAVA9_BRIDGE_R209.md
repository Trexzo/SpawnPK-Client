# R209 — Java 9 source legality bridge for original v309 widget class/package collisions

Client-side original-source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). Stacked on [R207 #1094](https://github.com/Trexzo/SpawnPK-Client/pull/1094), alongside the separate R208 deobfuscation crosswalk workstream. **This is an actual Javac legality gate, not recovered executable game code.**

## Independent original binary evidence

The exact SHA-pinned original v309 client JAR has 10,502 classfile entries, and **173 original class names are also JVM package prefixes**. Java source cannot compile a class and a same-qualified-name package concurrently. The affected actual original v309 owners include:

| Exact original JVM owner | Size | SHA256 | Verified observation |
| --- | ---: | --- | --- |
| `rs/n` | 242 B | `47d084fedbd212af8d3d8622fe894b476de6e911b3a88a50b3a87a92dbaa0cf7` | Another ancestor class/package shadow |
| `rs/n/c` | 340 B | `65b1517e3630da9dcc79b8e53c28fa1622c000ff0825b33880ca3262d4d2b2a0` | The independently recovered abstract widget superclass in R207 |
| `rs/n/c/ap` | 16,015 B | `b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4` | Original spellbook parent, original direct superclass rs/n/c |

Original client JAR SHA256:
`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

R207 separately proved original `rs/n/c.java` methods against that binary; R205/R206 have independently verified selected parent `rs/n/c/ap.java` method Code, but used an invented superclass `rs/n/c/c` for Javac. **That does not prove a single original-named Java compilation or identical superclass descriptor**, because the original binary class/package names are not legal in a single Java 9 source compilation.

## Stable name mapping, not original-byte equivalence

The existing [R125 private-client namespace legalizer](../src/spk_recovery/private_client_namespace_legalizer_r125.py) deterministically renames **the blocking type**, not an entire original child package subtree. The R209 private original-JAR verifier calls the same full-JAR R125 planner, validates the original base and child SHA-256 fingerprints, directly checks the original `rs/n/c/ap` superclass edge, and requires the mapped owner and child to be distinct, globally Java/Windows-safe and nonshadowing.

For the isolated `rs/n/c` blocker, the planned type naming follows R125's `c__Type_<sha256(original JVM owner)[:12]>` convention. This is an **explicit Java source representation**, not an assertion that the original binary class had this name. Do not hand-author a custom alias in one file while leaving original references or superclass descriptors inconsistent. Preserve R125's full remap plan as the authoritative source-wide class identity map; a class may have other dependent references, nested names, or package conflicts elsewhere.

## Actual Java9 compilation regression

The new R209 hosted test builds a completely invented `toy/widget/Base` and `toy/widget/Base/Child` source pair. With both original owner names:

- `toy.widget.Base` is a class and `toy.widget.Base` is also a package;
- Java 9 compilation **must fail**.

The test then obtains the exact R125 type alias, changes only the invented type declaration and its child's `extends` reference, and recompiles with:

`javac --release 9 -g:none -proc:none -implicit:none -classpath EMPTY -sourcepath EMPTY`

- It **must succeed** with exactly two emitted classfiles.
- The emitted JVM subclass must retain the legal child owner and use the **mapped base owner** as its actual `super_class`, Java major 53.
- Source-identity mapping must be deterministic and a bijection across both deeper collision families and original nested class names.

Regression tests deliberately reject missing class/package collisions, inappropriate namespace mappings, forged original binary SHA inputs and invalid Java source owner names.

The hosted CI is unrelated invented source only. The original client JAR is an optional, privately supplied input to the full R209 class-hierarchy audit; game code is never loaded or executed. No original-derived Java or binaries are uploaded to GitHub Actions.

## Remaining client reconstruction work

1. Replay the R209 private full-JAR verifier on the exact original client, alongside R125 and any R208 accepted mapping.
2. Recompile independently proven original Java owners under ONE shared R125/deobfuscated legal namespace: widget base `rs/n/c`, spellbook parent `rs/n/c/ap`, its enums and superclass references. Then compare every rebuilt method's JVM Code after remapping expected owner descriptors.
3. Accept original source behavior **separately from** original classfile byte identity, superclass name remapping, enum alias differences, StackMapTable representations and runtime.
4. Combine accepted sources into the pinned private experimental tree and measure the SAME full-client JDK-only compiler frontier.

**No measured source-file increase, compiler-error decrease, full-client runtime/build success, or original source publication permission is claimed in R209.** Latest independently measured R203 source-tree frontier is 1,295 files / 2,358 compiler errors; other concurrent agents' source snapshots are not comparable without a shared SHA-pinned baseline.

Keep the PR DRAFT until dedicated CI and private exact-input/merged-source acceptance pass.
