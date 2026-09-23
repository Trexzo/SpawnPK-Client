# Chat 2 — exact-v308 ModelChecker semantics R61

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R61 is a separate non-canonical class-only semantic review batch for an exact-v308
development model-reference checker.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_7F3D780FDF9356FF9831`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/u` -> `CLIENT_CLASS_001005`

## `rs/u` -> `ModelChecker`

The class explicitly describes itself at runtime through surviving diagnostics:

- `[Model Checker] Could not find directory "..."`
- `[Model Checker] Checking <n> models from [...]..`
- `[Model Checker] Found model ID ... for ITEM ...`
- `[Model Checker] Found model ID ... for NPC ...`
- `[Model Checker] Found model ID ... for OBJECT ...`
- `[Model Checker] Found model ID ... for GFX ...`
- `[Model Checker] Model scan complete! Found a total of <n> used models..`

The directory scanner enumerates files, strips `.dat` and `.gz`, parses numeric
filenames into model ids and forwards that set to the definition-reference scanner.

The second stage checks those model ids against:

- item model id;
- item male/female equipment model fields;
- NPC model arrays;
- object model arrays;
- GFX model ids.

Matched ids are collected into one used-model set and summarized at the end.

The semantic identity is therefore explicit: `ModelChecker`.

## Naming boundary

R61 uses the class's own surviving diagnostics as primary semantic evidence. It does not
claim any additional original-source identifiers.

## Acceptance boundary

Chat 2 does not promote R61. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_7F3D780FDF9356FF9831`.
