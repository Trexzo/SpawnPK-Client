# R145 — restore original-game-linked non-rs classes **as Java source**

Scope: v309 original client reconstruction only, **not the nonoriginal server emulator**. Stacked on [R144 #1031](https://github.com/Trexzo/SpawnPK-Client/pull/1031) and blocked final-source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Concrete original v309 blocker

The original SHA-pinned JAR contains **10,502** JVM classes. R136's graph proves that **8** original classes outside `rs/` directly reference `rs/`; they must be excluded from any nominally third-party binary-only compiler classpath. A private original-class inventory inspected on 2026-10-14 found **one relevant game implementation class** in this excluded group, `com/a/b/a/b.class`, and **seven tool/test investigation classfiles**. The Java client candidate has no `com/a/b/a/b.java` source. Independent private javac output from 1,271 actual source files after R144 shows **42 direct missing-class `b` diagnostics plus additional dependent use-site errors**. The matrix owner exists as original bytecode, but placing that original class back on javac's classpath would violate the no-original-game-binary-fallback milestone.

R145 introduces a **real private source-ownership compilation bridge**, not a bytecode stub or fictitious clean dependency:

1. SHA-pin the *whole* original JAR, whole original-derived Java source archive and a separately supplied **one Java-class source donor ZIP**. Original class must belong to R136's proven **direct** non-`rs/` game-linked binary partition; reject other classes, inner-only donor identities, duplicate files, archive/path/casefold conflicts and mutated pins.
2. Parse donor source with the installed trusted Java compiler AST; require exactly one Java declaration with the exact same JVM top-level binary name as the previously excluded original classfile.
3. Privately add the donor Java source to the unchanged full candidate Java source set in a disposable complete source ZIP, with no original game binary supplied to the compiler.
4. Run R137 twice, **both against the same exact R138 collision-normalized, R136 game-binary-excluded provisional non-`rs/` capsule**; compare total untruncated observed errors, code-file counts, original graph partitions, classpath hash and diagnostics SHA. Never accept the donor merely because javac errors decrease, or even reach zero.
5. Emit only a sanitized private report. Original client, source files, Java donors, generated classfiles, compiler messages and identifier-bearing partition are never checked into public GitHub or executed as client code.

## Synthetic end-to-end proof

Cross-platform workflow builds original Java9 `rs/Game.class`, an original non-`rs/` linked `ext/Bridge.class`, and an independent `ext/Clean.class`. The source candidate contains Java `rs.Game` and Java `rs.App` which calls `ext.Bridge`. Baseline javac fails because the original linked `ext/Bridge.class` is excluded; supplying a separately recovered **Java** `ext/Bridge.java` must make the full Java candidate compile, without admitting the game-linked original classfile. A clean/unlinked donor, wrong Java declaration, multiple donor classes and SHA mismatch abort.

## Private original-v309 command

```text
python -m spk_recovery.private_v309_game_linked_source_bridge_r145 \
  ORIGINAL_DERIVED_CLIENT_SOURCE.zip ORIGINAL_V309.jar PRIVATE_RECOVERED_ONE_CLASS_JAVA.zip \
  FRESH_PRIVATE_R145_COMPILER_REPORT.json \
  --source-sha256 2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536 \
  --donor-sha256 VERIFIED_PRIVATE_RECOVERED_CLASS_JAVA_ZIP_SHA256
```

Expected whole-original v309 SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Neither `rs/` originals nor the eight original game-linked binaries are allowed on the diagnostic classpath. The 9,335 remaining original-derived non-`rs/` classes still **are not certified independently owned/licensed dependencies**.

**Current limitation:** This PR does not itself decompile/rebuild the original game-linked matrix owner; its exact owner source must be recovered privately and independently proved with class/method/Code parity. R145 is only the safe way to measure such a verified source candidate in the whole v309 compile, without gaming the error count by reintroducing the original binary. The independently observed post-R144 516 remaining javac errors are not automatically reduced by R145; until a verified real Java donor is supplied, there is **no real v309 R145 error reduction**.

Original `rs/` first-party class/member provenance, thousands of non-`rs/` external binaries' ownership, Lombok-origin hypotheses, source package aliases and runtime parity remain separate. No release of full `recovered-source/v309/src/` is authorized yet.


## Original v308 → v309 exact-byte source reuse evidence

**Verified privately on the actual SHA-pinned user asset archive on 2026-10-14:** the original linked matrix owner `com/a/b/a/b.class` is **byte-for-byte identical** in v308 and v309, with class-byte SHA-256 `52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030`. Whole-client pins are v308 `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6` and v309 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

This is unusually useful for the user's versioned original-client Java source-tree roadmap: a separately accepted, original-proven, compiled-Java-equivalent recovery of this *specific owner class* can potentially be reused between the two versions because the entire original class bytes — not simply its name or API — agree. It does **not** prove the surrounding game model classes, dependency versions, source-generated names or runtime behavior are identical.

R145 now optionally accepts `--cross-version-original-jar PRIVATE_ORIGINAL_V308.jar --cross-version-sha256 854f26ff...` and compares the exact single original linked-owner `.class` bytes against the currently pinned v309 owner. Both whole original-archive hashes are guarded before and after replay. The sanitized JSON report records the cross-version input digest, selected-owner class digest, exact-byte identity boolean and explicitly `cross_version_source_semantic_name_carry_forward_accepted=false`. It never copies either original classfile into the source compile classpath. CI tests positive exact-byte identity, negative changed original owner and changed whole-JAR SHA. No recovered original Java matrix class has been accepted yet; the byte match alone is a reuse constraint, not a compilation result or source parity proof.

Example extra private CLI options:

```text
--cross-version-original-jar PRIVATE_ORIGINAL_V308.jar --cross-version-sha256 854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6
```
