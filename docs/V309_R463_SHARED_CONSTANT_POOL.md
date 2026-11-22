# R463 — Share one immutable Java 11 constant-pool byte decode across R450/R453/R458

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R462 draft PR #1259, head `63c486f7`, **all 4 platform jobs plus Recovery and inherited R450/R451/R456/R461 green**.  
**State:** DRAFT, UNMERGED, READ-ONLY STATIC INSPECTION ONLY.

## Why this optimization is justified

R459's consolidated audit eliminated repeated physical classfile reopening, R461 reused JVM `Code` opcode boundaries, and R462 reused validated generic Signature grammar results, but the three independent R450, R453 and R458 readers still performed their **own byte-by-byte constant-pool decoding** on the **same SHA-admitted, immutable Java11 classfile data**. Each scanned CP tags 1–20 and decoded UTF-8/string/class/member-reference indexes independently. These were distinguishable stages: repeated *tokenization*, versus important **independent semantic validation** (generic signatures, typed member names/descriptors, dynamic bootstrap/MethodHandle references).

R463 introduces `tools/r463/constant_pool_view.py` with a strict, bounded Java11 constant-pool decoder whose output is an **ephemeral, frozen** `Pool` containing immutable tuples of CP tags/values and the exact first byte offset after the pool. Integer/float/long/double values are intentionally opaque exactly as in the three existing parsers; long/double still occupy two CP slots. UTF malformed replacement behavior is retained. Unknown tags, truncated CP entries, invalid major and double-slot overflow fail closed.

**Critical custody rule:** `Pool.validate_for(raw)` requires the *same original immutable `bytes` object by identity*, not merely equal contents. A CP view cannot be transplanted between two classfiles, even if one has an equal copy of the bytes. The pool is never persisted, uploaded, stored globally, shared across audits or written to disk.

## Narrow integration and preserved validation

The three original parsers now accept an **optional keyword-only `shared_pool`**:
- R450 `classfile_evidence(raw, ..., shared_pool=...)`: retains all original Signature grammar, typed resource/API call, exact Code attribute parser and JVM instruction-boundary checks.
- R453 `parse_class(raw, shared_pool=...)`: retains strict Java11 default, Java8–11 optional dependency admission, all reference names/descriptors, class/field/method/interface declarations, duplicate validation and classfile trailing-data checks.
- R458 `scan_class(raw, shared_pool=...)`: retains strict MethodHandle and `BootstrapMethods` semantic validation, `CONSTANT_Dynamic`, `invokedynamic`, reserved byte, descriptor and CP tag checks.
- With **no** `shared_pool`, **all three use their unchanged original, independent byte-level CP parsers**. This keeps older owner-only R447–R458 tools and downstream client/source checks compatible. On a supplied view, each adapter still performs independent semantic checks; a wrong view type or class byte identity is refused.
- **Only the R459 consolidated evidence pass** invokes `cpview.parse(data)` once after per-file SHA verification and passes the resulting view to those three readers. R459 still performs two independent full owner R446 source/class/dependency SHA observations plus the single class evidence file read. This optimization removes repeated *in-memory CP tokenization*, not the required independent custody scans.

The new aggregate keys `R463_shared_constant_pool_decodes` and `R463_constant_pool_adapters_per_class=3` count exactly what was reused without exporting private CP entries, source/class names, method signatures, original bytes or user paths. R461 Code/Opcode and R462 generic Signature memoization remain available inside the one R459 inspection scope with unchanged strict bounds.

## Validation and risks

**30 fabricated regression tests** cover CP tag layouts and immutable view, all three reader outputs on independent invented R450/R453/R458 Java11 classes (including `invokedynamic` and `CONSTANT_Dynamic`), exact raw identity, wrong CP view type/owner, truncated/malformed records, unsupported tags/major, special method handles and bootstrap error retention, generic Signature error retention, Java8-only dependency parser unchanged, and owner fake **full public aggregate and private worklist equivalence** when the three readers ignore the shared CP option. Per-class parser call counts verify exactly one `cpview.parse` per rebuilt class evidence pass.

GitHub Actions runs Windows/Ubuntu × Python 3.11/3.13, all inherited R462–R445, R442/R426 synthetic suites, and explicitly labeled synthetic R461 profile and R460 benchmark commands. The read-count benchmark is for audit throughput only, **not client runtime latency or FPS**. Even a faster invented fixture cannot establish real-world R421 speedup. No real source, class/JAR bytes, private member names, player histories, credentials or resource assets are uploaded to GitHub.

## Remaining limitations

The owner desktop `DESKTOP-LTXXO4K` remains offline. No real 1,277 Java source/1,394 compiled class rebuilt R421 corpus, exact original 10,502-class v309 archive, or live v312 JAR were rechecked by R463 at time of implementation. The independently approved **historical full R421 source/class inventory** remains missing; current SHA inventory checks cannot replace it. Real JVM linking, complete deobfuscation, an asset-packed runnable client, GUI, login, player behavior, or performance acceptance remain **unverified**.

**Keep PR draft/unmerged.** No private source upload, game client replacement, destructive cleanup, player-history reads or writes, R415/R417 deletion-intent marker cleanup, persistence write-fence bypass, or release is authorized.
