# R129 — source-first Java9 class replay against the exact original v309 client

## Deliverable and scope

This milestone turns R127/R128's **review-only source↔original class suggestions** and the first private 79-instruction recovery experiment into a reusable **independently source-compiled JVM evidence gate**. The tool builds selected recovered Java source files without using *any* existing SpawnPK `rs/` bytecode (or third-party project binaries) as javac fallback. The original client is supplied only as a separately SHA-pinned, read-only **comparison** JAR after compilation.

This is **client-only**. It does not import independent emulator/server source, does not retrieve or execute the live client and does not attempt to contact production SpawnPK services.

## Process

1. Require an existing private source directory and a **new, empty-target** private output path. Recursively enumerate at most 256 regular `.java` source files (size and directory symlink bounds); disallow casefold-identical source filenames.
2. Independently hash every input source. Invoke an installed JDK's `javac --release 9 -g:none -proc:none -encoding UTF-8 -implicit:none` with an **explicitly empty `-classpath` and `-sourcepath`**. Only the enumerated `.java` paths are compiler inputs. This intentionally **fails** if the recovered class still depends on original client classes that were not independently restored as source.
3. Check every generated classfile has Java9 major version 53; reject unexpected output files, invalid ZIP/classfile signatures and case-insensitive output class filename collisions. Deterministically package the independently compiled classes in a private candidate JAR.
4. Check the requested `rs/...class` entry is present **exactly once** in the source-compiled output. Run the repository's established, independently pinned `source_class_method_matrix.build_class_method_matrix` on that private candidate and the exact original client JAR. It evaluates class headers, signatures, fields, individual method bodies, resolved instructions, JVM frames and exception handlers within its previously documented research scope.
5. Verify the copied candidate output SHA-256 before promoting **only** the private candidate JAR and sanitized matrix summary into the fresh local directory. Never place private Java, recovered member names, binary slices or local user data into public GitHub.

The output distinguishes `source_compile_succeeded`, `all_method_bodies_instruction_parity`, `field_inventory_exact`, `class_header_exact` and `all_matrix_checks_exact`. A normal compilation with a changed source method can legitimately produce an **unequal** research report; do not interpret compilation success as original binary equivalence.

```text
python -m spk_recovery.private_v309_java9_source_class_matrix_r129 \
 PRIVATE_RESTORED_JAVA_SOURCE_ROOT ORIGINAL_V309.jar \
 NEW_PRIVATE_OUTPUT_DIRECTORY \
 --class-entry rs/example/ExactRestoredOwner.class
```

Default original v309 SHA-256 is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. The alternate `--original-sha256` flag exists for **independent synthetic test fixtures**, not to quietly substitute a different official v309 client.

## Acceptance boundaries

A complete positive method matrix is a *class-level research finding* and does **not** prove authorial Java source identity, class initialization dependence on other recovered project code, undocumented Code subattributes, networking correctness, production runtime compatibility or the entire client. The emitted `original_game_class_parity_accepted`, `whole_client_source_tree_complete`, `whole_client_runtime_equivalent` and `source_authorial_identity_proven` remain **false**, including when all matrix checks are exact.

Some original client classes require source-compiled post-javac **StackMapTable metadata-only re-encoding** to express semantically equal verifier states. R129 does **not** perform that repair or copy executable Code bytes; the specific R116/R117 verifier provenance gates remain separate. When an uncorrected source-built candidate differs only by verifier metadata, R129 reports the difference until separately proven repair is applied.

## Tests

Ubuntu and Windows CI genuinely compile a tiny **synthetic** Java9 `rs/` class as an independent original reference, compile the identical source through R129 and compare actual JVM method/field evidence. Negative fixtures cover changed method body, SHA mismatch, unavailable compiler, invalid source, occupied output, unsafe class entries, and a precompiled `OnlyBinary.class` deliberately placed in the source tree that **cannot** satisfy javac because both lookup lanes are empty. Neither original proprietary JAR nor actual private recovered source is in GitHub CI.

## Next source-tree work

Use the independently reviewed R127/R128 source↔original pairs to select self-contained classes, **recover original member identities from binary evidence**, run R129 source compiles and assign stable accepted `CLIENT_CLASS`/field/method logical IDs only after deeper parity/lineage proof. Expand complete source dependency clusters, fix decompiler-generated compiler errors and namespace collisions, then run a full-tree Java compilation with **zero original game classfile fallback**. Publish `recovered-source/v309/src/` only upon complete source/build/runtime acceptance and confirmed rights to publish the derivative client; do the same independently for each later client build.

The authoritative project completion milestone remains [issue #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).
