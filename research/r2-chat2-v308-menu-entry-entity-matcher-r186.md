# Chat 2 — exact-v308 Menu Entry Swapper entity matcher R186

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R186 is a separate non-canonical class-only review for the tiny predicate interface consumed
by the reviewed Menu Entry Swapper plugin.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_3CD1782EB7D5B67330DF`
- field/method proposals: **0**

## Stable ID

`rs/s/l/a` -> `CLIENT_CLASS_000926` -> `MenuEntryEntityMatcher`

## Surviving exact method name

Unlike most of the client, the interface method name survives unobfuscated:

`boolean isMatchingEntity(int, int)`

The interface has:

- no fields;
- exactly one abstract method;
- no unrelated behavior.

That sharply constrains the class responsibility.

## Exact Menu Entry Swapper ownership

Reviewed `MenuEntrySwapperPlugin` (`rs/s/l/c`) owns **three** final
`rs/s/l/a` instances.

Its constructor initializes each through an invokedynamic lambda whose target method name is
also `isMatchingEntity`.

The plugin later passes these predicates into its menu-entry search/swap helper.

That helper scans menu entries and invokes:

`isMatchingEntity(candidateEntityId, targetEntityId)`

before selecting the entry index that will be swapped/reordered.

## Naming boundary

`MenuEntryEntityMatcher` is **0.999**.

The class name itself is descriptive, but its predicate responsibility is unusually strong
because the surviving exact method name already states the core behavior.

R186 deliberately does not infer separate NPC/object/item matcher class names: exact v308
uses three lambda instances of the same interface, and their higher-level category labels are
not required to name the interface itself.

## Acceptance boundary

R186 remains class-only and non-canonical. Main/Core may accept this proposal only through an
explicit `semantic_acceptance_spec` bound to `SEMREVIEW_3CD1782EB7D5B67330DF`.
