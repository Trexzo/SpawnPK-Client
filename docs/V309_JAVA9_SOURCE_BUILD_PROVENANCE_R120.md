# R120 — private Java 9 source-build witness for R119

## Purpose

R119 accepts one SHA-pinned post-javac Java9 candidate, but structural bytecode comparisons alone do **not** prove that input came from independent Java source. R120 adds a separate reproducible, **source-first** private compilation path.

The tool reads all regular `.java` files beneath a **private source directory**, checks bounded file counts/sizes and rejects symlinks. It invokes the locally installed `javac` without shell expansion, with `--release 9 -g:none -proc:none -encoding UTF-8`, an **explicitly empty classpath and sourcepath**, and no original or other project-binary JAR/class fallback. Every non-JDK dependency must be part of the explicitly compiled Java sources. The actual recovered owner, four source-legal nested enums, and any necessary **nonoriginal dependency stubs** must all be present as ordinary private source files.

The Java9 output is archived deterministically with a stable ZIP member order and metadata. The verifier rejects missing/malformed owner classfiles, mismatched Java9 classfile versions, an owner without **126 fields and 10 methods**, and any count other than **exactly four directly nested enum classfiles**, one named with the temporary legal fourth-enum surrogate. It checks each nested class's Enum access flag. The SHA-256 of the final staged copied candidate must still equal the freshly compiled JAR. Only a new private output directory receives the JAR and sanitized counts/digests; private source files, class/member names, compiler errors and all original client data remain outside public GitHub.

## How to use (private source only)

```text
python -m spk_recovery.private_v309_source_build_witness_r120 PRIVATE_JAVA_SOURCE_DIR ORIGINAL_OWNER.class SURROGATE_SIMPLE_NAME FRESH_PRIVATE_OUTPUT
```

This creates `FRESH_PRIVATE_OUTPUT/source-compiled.private.jar` plus `source-compiled.aggregate.json`. Feed the **new** candidate JAR and its SHA-256 into R119's original-v309 acceptance CLI. R120 by itself checks *compilation provenance and basic original-like declaration inventory*, not exact original-binary instruction parity. R119 must still pass its R116 → R117 → R118 chain against the separately SHA-pinned original JAR.

## Constraints and honest limits

The available private R110 cumulative artifact has a **partial** outer owner. It lacks a complete 213-instruction initializer and all ten final owner bodies within one source file; R120 must reject this incomplete artifact rather than label it accepted.

R120's hosted Java9 tests are synthetic and deliberately have trivial method bodies. They prove fresh Java9 source compilation, deterministic rebuild digest, field/enum count vetoes, malformed source failure and output no-clobber—not reconstructed original gameplay. No complete private original-v309 R120→R119 replay has been performed. Even a successful replay would not prove original authorial Java identity or runtime behavior of external helpers, callbacks, filesystems, networking or the whole game.

Do not upload private original-derived Java sources, original client binaries, private compiled candidates, credentials or user runtime configuration to public GitHub.
