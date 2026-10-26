# v311: 31 original Java sources — second connected dependency expansion

**Date:** 2026-10-21. Original user-supplied v311 JAR is private, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Source reconstructions, classfiles, original JAR and test harnesses remain in a **private working tree**, not the public GitHub repo.

## Actual source-build result

Extended the [previous 25-source island](V311_TWENTYFIVE_CONNECTED_SOURCE_ISLAND.md) by **six original v311 classes**. All **31 selected Java 9 sources compiled together in one `javac --release 9 -proc:none -g:none` invocation**, using empty original game binary classpath/sourcepath, with the existing `rs/t` compile-only class alias confined to the private disposable source overlay.

The 31 independently compiled classes were inverse-remapped in **copied classfile metadata**, restoring `rs/t` as the original JVM type identity before `javap -c -p -s` comparison. For **31/31 classes**, original class declarations and **767/767 ordered JVM instructions, exact byte offsets, branch targets and symbolic field/method operands matched**, normalizing only constant-pool numeric indexes. The two verified `rs/g/e` original exception handler rows also matched. These are JVM symbolic instruction/declaration parity witnesses, not SHA-identical original classfiles or complete attribute/StackMapTable identity.

| New original class | Original SHA-256 | Source-recompiled class SHA-256 | Original instructions matched |
|---|---|---|---:|
| `rs/a.class` | `7c33983b6e49dc2cd8b4b5bde2bd0550a4977c1eaa483025630b5c16105e735f` | `efb0ded6bb5ea73f8fd5563ddb5e1708a7ec4b7c688d13bac597eb26a0073e4b` | 24/24 |
| `rs/N.class` | `50c92698bec48e9af29cac57beb319554bb8226673729c4a6657e600ab518363` | `a593903e3434a0e7a1611d99a261571a3f1e2cf4aad2434611f22d5a6a33d92b` | 6/6 |
| `rs/y/b.class` | `5535343f6f7fe8d852b0e42f1d4350e3baf75b2be312fbe9cbcb9f04dd4bfc32` | `e2f55eaacb726c8785ee66c655978d27e15ae77143f00eb9df41f08014de3bc4` | 3/3 |
| `rs/y/c.class` | `98c06b541407a72771e6e172130b781eb799da4259abbd45748b9f08c0e3b8a8` | `463be801ff0c0ec4bc8db1e68656c36d4552554f6a107870f1ccb6b3872873fd` | 0/0 (interface declarations) |
| `rs/ui/components/q.class` | `8aa491819d87031af452dfaad452c98dafe4d276b121f2cd1c0a5e4f67610f30` | `361a66f260dda359a91c8980015f126780258264f4d8a95fe3fbc34310a6a33e` | 0/0 (interface declarations) |
| `rs/ui/components/w.class` | `cca4907c0111fbe5de3f8e916c84cb38b9cc11ca75e759dc4a0905a13a3f0e1d` | `a574bab10a5c7adf2a062d512c9c81acb683789830c2b55d7ac88bb10493e8d2` | 0/0 (interface declarations) |
| **Six-class addition** | | | **33/33** |
| **Combined 31-class source island** | | | **767/767** |

Actual private compiled class-path/SHA manifest digest: `d09609eafe3854dbf4c03a2e13a0bfbb12f2cdf883eefa0856da8605142b63a9`.

The strict original classfile constant-pool reference census returns **31 selected classes, six explicit cross-project class dependency edges and zero unselected explicit project-class references**. New dependencies include `rs/a → rs/t`, `rs/N → rs/t`, `rs/y/b → rs/y/c` and `rs/ui/components/q → rs/ui/components/w`, beyond the three edges in the preceding 25-source island. Two more explicit references to `rs/t` require treating its temporary compile alias as a true **source-island identity mapping**, not merely a local class-declaration replacement.

## Zero-instruction original interfaces: still require complete declarations

Three of the six added original classes are interfaces whose classfiles
contain **zero `Code` instructions**. They must not be labeled unrecovered
merely because they have no executable methods, nor accepted based only on a
matching empty instruction list. The updated source-parity verifier accepts
zero instructions **only** for a class declaration that is actually an
`interface` and still has matching declared methods and their JVM
descriptors. Concrete classes without `Code` continue to fail closed.

A new synthetic Java9 regression compiles two interface-only original
fixtures with inheritance, verifies exact declaration/descriptor parity and
one original inter-interface dependency, while another regression rejects a
truncated concrete-class disassembly. The actual three v311 original
interfaces were separately inspected and source-compiled **privately**.

## Original-vs-rebuilt offline behavior and class-shape probe

In an isolated JDK classloader, original and rebuilt implementations agreed on linked-node splice/unlink behavior, repeated unlink idempotence, the derived data-holder's `g=-1` and other zero-initialized fields, and reflection-verified abstract class/interface inheritance shapes. This is a bounded offline JDK probe; it does not verify original game rendering, login, client server calls, concurrent behavior or every class method.

## Improved source-only alias evidence

`src/spk_recovery/standalone_source_alias.py` now provides the strict `rewrite_reviewed_external_superclass_alias` transformation. It permits only a **same-package `class Child extends Original`** superclass reference, after exact alias-name/package validation, and rejects unreviewed old-name occurrences as fields, constructors, method returns, expressions or cross-package references. Every source edit is staged in a private disposable copy **before compiling**; canonical sources are never modified. The existing `standalone_source_parity.py` already inverse-remaps the actual emitted JVM class metadata, not textual `javap` output, before original-name instruction comparison. Synthetic CI adds an end-to-end three-class Java9 source build containing the `rs.t` class, a `rs.t.f` package class, and a third original class extending `rs.t`; it also tests refusal on unsupported alias contexts and missing class dependencies.

**Scope limits:** The six new sources and their private classfiles are not in hosted CI. Hosted CI verifies the reusable tooling with unrelated synthetic Java, including checked superclass references. This is not a recovered/full-source v311 client; 31/1,184 project classes were source-compiled in the private island. Remaining original binary identity, full metadata parity, runtime dynamic references and original v309-to-v311 member lineage have not been certified.

**Next milestone:** expand into a real larger linked-node utility subsystem and subsequent GUI event/scene support classes, requiring fully reviewed source field/method alias references rather than blanket lexical substitutions. Do not weaken the fail-closed alias guard merely to increase the class count.
