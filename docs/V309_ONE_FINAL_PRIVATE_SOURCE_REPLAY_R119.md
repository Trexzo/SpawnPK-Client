# R119 — one private original-v309 source-compiled acceptance replay

## Scope and prerequisite

R119 orchestrates the **existing** SHA-pinned original binary acceptance chain; it **does not** decompile Java, recover missing source, compile private Java, or prove whole-gameplay equivalence. It consumes one independently Java 9-source-compiled owner candidate containing **126 original fields, 10 original methods, 93 initializer writes and four source-legal nested enums**. The original complete JAR must match the hard-coded v309 SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Both JARs must be separate existing private files.

The public GitHub repository contains **only orchestration code, synthetic tests and sanitized documentation**. It deliberately does not contain the original client JAR, original-derived Java source or literals, proprietary classfiles or private sample output.

## Exact ordered chain on one source candidate

1. **R116 → R113:** repair only the original 364-op saver StackMap second frame; demand verified original 364 operands and all ten frames. Save its SHA-pinned candidate only in a temporary private working area.
2. **R117 → R81:** take exactly the R116 output; restore 161 original symbolic loader verification states at candidate Java9 instruction positions. Require unchanged candidate 697-op executable Code and the accepted R116 saver.
3. **R118 → R106/R105/R104/R95 → R94/R58/R88:** take exactly the R117 output; verify all four nested enums, nine ordinary owner methods, 213 initializer instructions / 93 ordered writes, and original 126-field/10-method declaration set.
4. **Fail-closed promotion:** independently check the SHA-256 of every intermediate JAR and original/input files, distinct candidate digests at each stage, every acceptance flag, and absent destination. Publish **only** the final private candidate JAR and one sanitized aggregate JSON if *all* checks pass. Failure leaves no accepted output. All staging is temporary.

The top-level CLI additionally refuses a wrong or caller-selected original v309 SHA-256. It does not execute the original client. It does not copy original executable Code bytes into generated classfiles. External stubs do not establish real helper behavior.

## Private command

Run in an environment where `spk_recovery` is installed, with the actual private separately source-compiled Java9 candidate:

```text
python -m spk_recovery.private_v309_three_stage_replay_r119 ORIGINAL_V309.jar SOURCE_COMPILED_OWNER.jar ORIGINAL_OWNER.class SURROGATE_SIMPLE_NAME NEW_PRIVATE_OUTPUT --original-sha256 ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38 --candidate-sha256 <independently computed 64-digit SHA256>
```

The `SOURCE_COMPILED_OWNER.jar` is the **unrepaired Java9 source output**, not an R116/R117/R118 intermediate. R119 controls the three stages itself. `NEW_PRIVATE_OUTPUT` must not exist.

## Evidence and limitations

Synthetic hosted tests prove ordered invocation, candidate SHA forwarding, input integrity, canonical original pin refusal, and negative stage/mismatch/output cases. **No exact-original R119 CLI replay was completed as part of these synthetic tests.** In the current known user Library, the R110 cumulative source bundle contains the 126-field/eight-final **partial** owner rather than one full ten-method source candidate. That partial bundle must never be passed as if R119 source acceptance succeeded.

Even a successful independent original-v309 R119 replay certifies only the **bounded reconstructed owner and nested-enum JVM comparison**, not authorial source identity, original nonowner helper implementation, configuration and filesystem behavior, callback/network integration, whole-gameplay or runtime equivalence.
