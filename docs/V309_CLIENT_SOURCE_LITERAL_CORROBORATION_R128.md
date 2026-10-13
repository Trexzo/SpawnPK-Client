# R128 — independently corroborate R127 class-shape candidates with string literals

## Evidence, not acceptance

R126's actual source-JVM AST census showed that **1,271 Java files parse cleanly** but only 28 named declarations share an original v309 `rs/` class spelling. R127's source field/method structural singleton pass produced **501 review-only proposals** on an independent private v309 dry run, including 486 name-changed candidate pairs. This is a useful queue but **not an accepted mapping**.

R128 reads the exact private source ZIP and v309 JAR (SHA-256 independently pinned). A separate trusted JDK `JavacTask.parse()` visitor inventories unescaped Java **string literal values** within each source top-level class, excluding named nested/anonymous classes whose JVM constant pools belong to other binary classes. Original classfile `CONSTANT_String` values are independently decoded from the pinned original by our existing `parse_class`. R127's unique shape proposal pairs are then classified with strings of length **at least six characters**: all present, some present, none present, or no informative source literal available.

A successful all-literal overlap does **not** prove original class identity; strings may be generic or shared, and decompiled source may omit compiler/annotation/reflective effects. Even with matching field and method signatures plus all literals, each class still needs independent original bytecode/callsite and accepted lineage evidence. R128 always reports **`original_class_lineage_accepted=false`** and **`literal_evidence_alone_accepts_class_identity=false`**. Original client and source Java are never executed or compiled as game code.

## Actual private dry-run frontier (not GitHub CI)

A local read-only implementation of equivalent source AST and JVM Constant_String decoding was run against the user's source ZIP SHA256 `2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536` and the original v309 SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

| R127 structural candidate class | Count |
|---|---:|
| Total unique structural proposals | **501** |
| Proposals with any source string literal | **266** |
| Proposals with an informative source literal (6+ chars) | **246** |
| Every informative source literal found in proposed original CP | **96** |
| At least one but not all informative literals found | **91** |
| No informative literal found in proposed original CP | **59** |
| No informative source literal available | **255** |

The 96 all-overlap cases are **prioritized corroboration candidates**, not approved deobfuscated classes; the 91 partial and 59 zero-overlap cases may indicate a wrong structural pairing or legitimate source/code-generation differences, requiring analysis rather than automatic rejection. The 255 cases with no informative literal have no extra evidence from this lane.

These private aggregate metrics are **not** an original-binary run of the finalized packaged R128 command or hosted CI, and no private literal values, class pair identifiers, Java source or client binary were published.

## Private invocation

```text
python -m spk_recovery.private_source_literal_corroboration_r128 \
  PRIVATE_DECOMPILED_SOURCE.zip PRIVATE_ORIGINAL_V309.jar \
  FRESH_PRIVATE_LITERAL_REPORT.json \
  --source-sha256 EXACT_PRIVATE_SOURCE_ZIP_SHA256
```

`--private-identifiers` is an **explicit local-only** mode producing candidate names and evidence tiers (not actual string literal content). The default report contains only SHA pins, deterministic manifest digest and aggregate tier counts. Neither output belongs in a public GitHub commit if identifiers are enabled. No server code, assets, account/profile files or user source are included.

## Next stage

Accept source↔original client class lineages only after original JVM method/callsite/constant and cross-version relationship proof, not from fields/method shapes and shared literals alone. Feed accepted identities into symbol-aware Java source editing, resolve R125 Windows/Java namespace collisions, then establish zero-original-`rs/` class fallback whole-project javac and original behavior/runtime acceptance under issue #1004. The deliverable remains a full source snapshot at `recovered-source/v309/src/`, then independently verified standalone snapshots for v310+.
