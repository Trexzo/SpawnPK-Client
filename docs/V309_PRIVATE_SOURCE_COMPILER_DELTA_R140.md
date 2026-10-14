# R140 — a measurable source compilation delta, without a false completion claim

**Stack:** R136 #1023 → R137 #1024 → R138 #1025 → R139 #1026 → R140. Original-client-only source recovery, milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

The current private source build baseline was 614 errors on the **unmodified** 1,271-Java candidate against the *non-normalized* provisional original-v309 non-rs diagnostic JAR. That number cannot truthfully be compared with a rewritten source candidate compiled against a different classpath.

R140 fixes measurement discipline: given the exact SHA-pinned original-v309 JAR and candidate source ZIP, run R139's AST-backed import overlay in private memory, materialize its entire updated Java file set into a disposable deterministic ZIP, then call the existing R137 compiler **twice with R138 collision normalization enabled**. The first run uses the untouched input source. The second uses the R139-edited source. Both run javac with Java release 11, disabled annotation processing, an empty external sourcepath, no ambient project classpath and precisely the same R136-filtered, R125/R8R-collision-normalized **original-derived and uncertified** non-rs classpath. The tool rejects altered classpath digests, original SHA drift, changed source coverage, any original rs game class direct fallback, source compilation being mislabelled as verified, or missing AST rewrite proof.

R140 produces just one **private sanitized JSON report**: source/version pins, code-file counts, R139 import changes, R138 classpath digest, pre/post actual compiler error totals, error-type splits and explicit improvement/unchanged/regression classification. Counts may be truncated at javac's configured cap, in which case comparisons must be called uninterpretable. No raw compiler stderr, class identity list, game binary, derived source ZIP or source file is published to GitHub. All temporary sources, original-derived capsules and compiler output are destroyed.

## Synthetic cross-platform evidence

Ubuntu and Windows CI construct actual independent Java9 classes under `ext/A`, `ext/a`, and `rs/` and independently call the full R136/R138/R139/R137 chain twice. The old import fails under R138's legal package alias and the AST-updated import compiles. A no-op source verifies unchanged counts, and SHA mismatches abort before source staging. This proves only the diagnostic runner and comparison, **not** original-v309 source compilation or any measured reduction against the user's real 1,271-source candidate.

## Private exact-v309 command

```text
python -m spk_recovery.private_v309_compile_delta_r140 PRIVATE_SOURCE.zip PRIVATE_ORIGINAL_v309.jar FRESH_PRIVATE_DELTA.json --source-sha256 EXACT_PRIVATE_SOURCE_ZIP_SHA256
```

The first original-v309 R140 report must not quote the old 614 number as an R138-normalized baseline unless independently observed. No automatic PR merge or publication follows a favorable result. More compiler blockers, source-to-original class/member parity, full runtime verification, independent dependency ownership, and redistribution rights remain unsolved.

**Final milestone is still a complete versioned compilable Java source tree under `recovered-source/v309/src/`, not these research tools.**
