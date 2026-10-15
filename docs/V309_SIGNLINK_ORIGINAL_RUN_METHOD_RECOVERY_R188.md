# R188 — original v309 client Signlink run() Java-source recovery

Stacked on [R187 #1080](https://github.com/Trexzo/SpawnPK-Client/pull/1080), tracked by client original-source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

## Independent private original Java-source result

The final original rs/v/a.run():void service loop has now been reconstructed as real original-named Java9 source, independently built **without the original client JAR or any external compiled classfile** on the compiler classpath. The compilation emits rs/v/a.class and exactly seven explicitly inventoried, invented **compiler-only** helper classes. No game code is executed.

- Pinned original v309 JAR SHA256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38
- Original rs/v/a.class SHA256: d0dc35deddc8016c3fdcaf2615810efa200c042120b83bed86cad5d04b1c0ddc
- Private exact run-candidate Java source text SHA256: 03d6b77ffa1b3eb77ee24d562b38a699e493f01739ab9303c17d7f344c859f77
- Private exact run-candidate Java source ZIP SHA256: a7172b3aae3a794bbd5a59f6de085a7ee7b68749a117671d5cf6b47a0fcd5288
- Private compiler-only seven-helper Java ZIP SHA256: 23d81085f2a692f5d6fc60791c489bb9982b104d569d4037d6d8aa4e75a13f3d
- Previous verified R187 23-method ZIP SHA256: 78d328edb230b5dd211b6f30b2d06f515221815ad1a801c01f3c6309d4acd59c

**Exact original run():void method Code:** 248/248 decoded JVM instructions, exact source compiler operation offsets from 0 through original final RETURN at offset 597, matching all branch targets, resolved method/field references, checked exception-handler entries, max_stack 6, max_locals 12. The source captures original network socket request, background-thread scheduling, hostname lookup, local sound-file saving, javax.sound.sampled source-data playback and pan control, music playback, URL stream request and 50ms generation-aware loop.

The private Java9 source-only recompilation uses JDK 21 javac --release 9 -g:none -proc:none -implicit:none, isolated empty compiled and source classpaths. A separate local javap comparison found an alternate StackMapTable representation in the final frame. **StackMapTable identity must be reported separately, never silently claimed from method Code identity.** New GitHub strict verifier compares CP-resolved original and rebuilt method Code and returns the actual frame parity boolean.

## Crucial distinction: method source vs fully recovered original class

R187 independently verifies **23/24 original JVM methods, 574/574 selected original instructions** from one private source-only Java class candidate. R188 independently verifies the **remaining run() method, 248/248 original instructions**, in a different private source-only candidate. Thus **all 24 method bodies have now been reconstructed individually**, with 822 originally matched instructions across TWO builds.

**THIS DOES NOT YET PROVE that all 24 methods match simultaneously when compiled from one Java source file.** The additional run() Java body changes Javac's constant-pool allocation; moving it earlier avoids nonoriginal ldc_w widening in run() but introduces ldc_w widening in several other original method bodies. Keeping the original R187 source ordering retains the other 23 method bodies but widens multiple constants inside run(). Tested numerous Java declaration positions; do not claim whole-class source parity from separately compiled method proofs.

The original class field declarations and method count match in the R188 run candidate, including the previously missing audio-direction field of type rs/v/a$a. However **rs/v/a$a is an original three-value enum**, while the R188 compiler-only helper is NOT its original Java source or runtime behavior. The six other compiler helpers are likewise NOT original classes. These helpers may not be released as recovered originals or executed as the game runtime. Some source-rebuilt method-level optional Exceptions and StackMap attributes differ. A complete runnable v309 client is not established.

## GitHub strict verifier and regression

The R188 SHA-pinned verifier:
- first independently replays R183→R184→R185→R186→R187 23-method private acceptance;
- pins the original JAR/class and BOTH new private candidate ZIPs;
- ensures the run candidate is the single original-named rs/v/a.java and only the exact seven enumerated compiler helper Java declarations are permitted;
- independently recompiles with JDK9 target and empty binary/original external classpath;
- verifies exact class owner/super/version/interface/access, full original 24-method inventory and complete declaration-level field ABI;
- compares run() Code via the established R150 strict symbolic JVM verifier (including resolved invokedynamic recipes, offset/code-length, stack/local limits, exception handlers);
- returns independently measured StackMapTable equality and explicitly marks full-class simultaneous acceptance, runtime, original helper source and canonical private integration as **false**.

Hosted Ubuntu/Windows CI uses only unrelated synthetic Java9 fixtures. No original JAR, original derived Java or sensitive runtime data enters public GitHub.

## Next acceptance gate

1. Reconcile constant-pool source declaration ordering or another **source-backed** legal compilation procedure to produce one private Java9 class with all 24 method Code streams simultaneously matching, including separate StackMapTable and non-Code attribute audits.
2. Recover original nested rs/v/a$a enum Java plus other six actual support-owner source bodies; eliminate compiler-only runtime helper declarations.
3. Measure full original-class ABI, full-client canonical source tree and SHA-pinned identical Javac error-frontier deltas, integrate with Packet R179 and ISAAC R182 only after they pass.
4. Verify source redistribution rights before publication. Do not claim original full-client compiler/runtime success or a reduction in the JDK-only error frontier.

Original reconstructed Java sources and raw binaries remain outside public GitHub and are not runnable as released game code. Keep PR DRAFT until private exact-input replay and all gates pass.
