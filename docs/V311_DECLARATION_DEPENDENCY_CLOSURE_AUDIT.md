# Original v311 — declaration-complete source dependency closure audit

**21 October 2026.** This audit uses the exact privately supplied official `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original JAR, disassembly and proprietary reconstructed Java remain private. No game runtime or account was accessed.

## Corrected false-closure condition

Previously, `source_dependency_closure.explicit_class_references()` only inspected `CONSTANT_Class` entries and `NameAndType` / `MethodType` descriptors. It **did not inspect the original class's own `field_info.descriptor_index` and `method_info.descriptor_index`**, which can contain field or abstract-method types absent from those constant-pool reference categories. It also did not read generic `Signature` attributes.

Concrete original-v311 counterexamples:

| Original classfile | Actual declaration-only dependency that the old checker missed |
|---|---|
| `rs/n.class`, SHA-256 `47d084fedbd212af8d3d8622fe894b476de6e911b3a88a50b3a87a92dbaa0cf7` | Fields of type `rs/a/a` |
| `rs/M.class`, SHA-256 `b30905685075a6b8a772c06c818900f80304dab0bf99ea84d8fa6261efef2e41` | Abstract method returns `rs/R` |

A size-only or constant-pool-class-only scan wrongly advertised those types as dependency-free. Neither counterexample may be accepted as a standalone source island without its declared types being present or explicitly reviewed.

## Replayed original JAR census

With the updated scanner, all **1,184/1,184 `rs/` original classfiles** parsed without errors.

| Metric | Previous checker | Declaration-aware checker |
|---|---:|---:|
| Original v311 project classes parsed | 1,184 | 1,184 |
| Explicit cross-project class dependency edges, excluding self | 4,961 | **5,008** |
| Newly identified direct dependencies | — | **47** |
| Classes affected by previously missed dependencies | — | **40** |

The new checker reads the original field and method descriptors from `field_info` and `method_info`, plus the formal `Signature` class/member attributes for generic source types. It validates member/attribute lengths and constant-pool indexes, and refuses truncated or malformed declarations. It deliberately does **not** regard literal strings resembling type descriptors as Java class dependencies.

The separately established set of **40 privately independently source-recompiled v311 classes** was also rechecked under the stronger scanner: **40 selected project classes, 15 explicit cross-project class edges, zero references outside that selected set**. Thus the prior genuine private compile/bytecode proofs remain valid; the bug affected dependency *discovery and closure assertion*, not the already verified symbolic JVM instruction parity. The 40 recovered sources are spread across separately attested source groups, not a full 40-class single-source compilation.

## Hosted regression and limits

The new `tests/test_v311_declaration_dependency_closure.py` compiles five actual unrelated synthetic Java 9 classfiles, with: an own field typed as a selected class; an abstract method with input and return types; a generic `List<Target>` signature whose erased field descriptor contains no Target; and a literal constant that only **resembles** a descriptor. It verifies the required type dependency, refusal of incomplete source selection **before generating output**, corrected frontier-candidate eligibility, and avoidance of the literal false positive.

The checker still does **not** claim full program closure for dynamic reflection, `ServiceLoader`, annotations in unparsed formats, invokedynamic bootstrap semantics, resource-loading, native code, or the runtime game environment. Classfile dependencies are a useful safe compile gate, not complete v311 source parity.

**Next engineering target:** rerun dependency-closed candidate prioritization with the improved scanner, then recover a meaningful scene or UI dependency class using the exact original source-to-JVM verification pipeline. Do not promote earlier source-frontier candidate lists without rescanning them.
