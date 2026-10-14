# R139 — safe explicit Java import overlay after R138 package legalization

**Scope:** original-v309 **client-side source repair only**, stacked on R138 → R137 → R136. The complete source target remains [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

R138 can normalize JVM-legal/Java-illegal original-derived **provisional non-rs classpath** names using R125/R8R. If R125 moves an entire Java package, an existing Java import can still name an old package. R139 introduces an **actual private Java source rewrite** for one narrowly defined case: explicit non-static class imports whose full name changed while the type's simple name remained exactly the same.

R139 derives eligible original binary names from the SHA-pinned R136 provisional non-rs partition, then replays R125 on that partition. It does not classify those binaries as certified third-party or allow any rs/ originals as classpath fallbacks. A trusted JDK JavacTask.parse() helper returns exact ImportTree positions, and Python checks the positions before editing imports. All other files remain byte-identical.

**Conservative boundaries:** no changed-simple-name class aliases, static imports, wildcard imports, declaration package names, qualified type uses outside the sole import, or unverified member expressions. If any import in a source file is unsafe, the entire file is kept unchanged for separate review. Input SHA mismatches, syntax errors and source-offset ambiguity abort.

## Synthetic proof versus actual client

The cross-platform fixture compiles real Java9 classes under ext/A/Target and ext/a/Other, which conflict on case-insensitive filesystem identity, plus original rs/Game. R125/R138 remaps the provisional external capsule. Java compilation fails with the unchanged import, and succeeds after the AST-located import edit without any original rs/ binary fallback.

This fixture validates the mechanism; it does **not** prove the exact real v309 upload has eligible imports, or that its 614 baseline compiler errors decrease. The private overlay result can be passed to R137/R138 to measure a new diagnostic count.

## Private command

    python -m spk_recovery.private_v309_import_overlay_r139 PRIVATE_CLIENT_SOURCE.zip PRIVATE_ORIGINAL_V309.jar FRESH_PRIVATE_OVERLAY.zip FRESH_PRIVATE_REPORT.json --source-sha256 EXACT_SOURCE_ARCHIVE_SHA

Outputs only a private full client-Java ZIP and sanitized report with SHA pins, source-file counts, mapping digests and explicit noncertification. Never upload original binaries, private source, identifier-bearing maps, cache or account files into public GitHub.

**Not accepted:** complete independently compiled original-client source, independently licensed dependency set, semantic class/member lineage, original code and StackMap parity, runtime compatibility, or rights to redistribute the decompiled source. The final recovered-source/v309/src/ milestone remains incomplete.
