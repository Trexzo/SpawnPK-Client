# Original v311 — 32 independently compiled Java classes and linked-node collection

**Date:** 2026-10-21. The following observations were made against the exact user-uploaded original `client(20261021-111920).jar` (SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`). The original binary, reconstructed Java, compiled classes and behavior probes remain private and are **not** committed to public GitHub.

## Real v311 recovery advancement

Added original `rs/h.class`, a circular linked-node collection implementing insertion, iteration, removal and clearing. It depends directly on already recovered `rs/t.class` through **field types, method descriptors, allocation and node-field/method instructions** — not merely through superclass inheritance.

| Original v311 class | Original class SHA-256 | Independently rebuilt class SHA-256 | JVM instruction comparison |
|---|---|---|---:|
| `rs/h.class` | `c1d9899c7ecb157e8e587b8fda9e661923d68c0a62a073164c152d073156788e` | `ef7fc0cba3f2907a97634c264bfcca51bafb11ad92527b3b7efdc05ef9aa3c6b` | **171/171 exact ordered symbolic instructions** |
| Previously verified 31 original classes | See [31-class evidence](V311_THIRTYONE_CONNECTED_SOURCE_ISLAND.md) | Their recompiled classfiles are SHA-identical to the previous accepted build | **767/767**, unchanged |
| **32-source combined evidence** | | | **938/938** |

All **32 selected Java source files compiled together** using `javac --release 9 -proc:none -g:none`, with explicit empty original-game classpath/sourcepath and a disposable compile-only class alias `rs/t.class → rs/RecoveredNodeV311.class`. **Exactly 32 Java 9 classfiles** were emitted. The original 31 recompiled classfiles are **byte-for-byte identical** to the prior verified 31-source build; the one newly emitted `rs/h.class` is identical to the separately compiled and independently verified `rs/h` trial classfile. Thus the 32-class instruction/declaration parity rests on the earlier 31-class verification plus one exact 171-instruction original-vs-rebuilt comparison. A separate attempt to replay all 32 `javap` comparisons in one bounded process exceeded the execution window and was interrupted; this is not presented as a separate completed 32-way replay.

Private compiled path/content SHA-256 manifest: `db45c7cb39e3254e605da1f47c18559916904317f9c8aaa05db6e16248b830ef`. The original `rs/t` name was restored in copied JVM class metadata before comparing symbolic operands/offsets/branches. The rebuilt complete classfile bytes are **not** represented as identical to the original.

The original constant-pool-based source-closure census reports **32 selected classes, 7 explicit original `rs/` cross-class dependency edges, 0 unselected explicit project dependencies**. It excludes dynamic/reflection/resource/native loading as before.

## Original-versus-rebuilt offline collection behavior

An independent Java reflection probe loaded the **exact original game JAR** and the 32-class inverse-name private compilation in separate URLClassLoaders. It constructed the real original `rs.t` node objects and `rs.h` collections, exercised initially empty state, insertion at both ends, forward and backward traversal, removal and clearing. Both produced the same labeled event sequence, `EBAC/CAB/BAC/E/E`, and the probe passed. This is bounded collection-level behavior equality, not gameplay, general thread safety or a server interaction.

## GitHub verifier improvements

The existing `standalone_source_alias.py` now admits additional **strictly recognized same-package original node-type references** in temporary compilation source copies: field/local/parameter/return types, superclass declarations and constructor allocations. Token-level recognition is used; it refuses ambiguous invocations, member access, class literals, reflection-like identifiers and cross-package references. Selected source files in unrelated packages that contain **no aliased identifier outside their own package declaration** pass through byte-for-byte unchanged, which is essential for the `rs.t` package descendant sources. Canonical private Java is not rewritten.

`standalone_source_parity.py` stages these typed references before the independent Java build and continues to inverse-remap emitted JVM classfile metadata using the existing checked remapper, then compares to exact SHA-pinned original JVM disassembly. Two new **synthetic-only** CI test modules exercise allowed/refused type contexts and compile a 3-class Java 9 source island containing a `rs.t` class, `rs.t.f` package child and a collection that refers to `rs.t` through fields, methods and allocation. Hosted CI does **not** have access to the real game JAR or private reconstructed sources.

The milestone is **32 of 1,184 original project classes**, not a complete independently compilable v311 client or a full classfile-attribute/binary-identical rebuild. Larger linked-node structures and later renderer/client support remain to be recovered. No historical R308 native game-launch acceptance or old ZIP archive is required for this source island.
