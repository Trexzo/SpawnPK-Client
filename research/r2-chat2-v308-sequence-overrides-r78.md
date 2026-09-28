# Chat 2 — exact-v308 sequence definition overrides R78

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R78 is a separate non-canonical class-only semantic review batch for the exact post-decode
sequence-definition override table.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_F29C3AB052BF15F0D4FC`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/d/b` -> `CLIENT_CLASS_000111`

## `rs/d/b` -> `SequenceDefinitionOverrides`

The class is entirely coupled to R28 `SequenceDefinition`.

Its two public static methods both receive one sequence id and index the global
SequenceDefinition array directly.

The first method contains a **106-case** id switch. The second contains a **73-case** id
switch. Matching cases replace exact definition fields including:

- frame counts;
- primary/secondary frame-id arrays;
- frame-duration arrays;
- interleave/order arrays;
- loop/replay and other playback-control values.

The decisive ownership signal is in the SequenceDefinition loader itself: after each
sequence record has gone through its ordinary decode/customization path, the loader invokes
both R78 methods with that same sequence id.

So this is not another animation format or loader. It is the exact deterministic
post-decode patch table applied to selected SequenceDefinition ids.

## Naming boundary

`SequenceDefinitionOverrides` is a semantic recovery name. R78 does not claim it is a
verbatim original SpawnPK developer identifier.

## Acceptance boundary

Chat 2 does not promote R78. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F29C3AB052BF15F0D4FC`.
