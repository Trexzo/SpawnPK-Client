# R8A exact-v308 source-safety acceptance

Date: 2026-09-22

This records Main/Core validation of R8A against the private exact-v308 client authority. No client JAR, transformed JAR, generated lineage, decompiled source, or proprietary asset is committed.

## Authority

- exact v308 SHA-256: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`
- branch under test: `core/r8a-source-safe-namespace`
- implementation head before this report: `5cb6c3305792eee8747067773f5e3ccdce252a07`
- accepted semantic review: `SEMREVIEW_DD69CD752A6E46181BAC`
- accepted semantic class remaps: 32

## Collision reproduction

The exact authority contains 1,129 `rs/**` classes.

Measured Java class/package collision roots:

```text
exact v308, before semantic remap: 88
after the 32 accepted semantic class remaps: 85
R8A source-safety fallbacks required: 85
after R8A fallback plan: 0
```

The fallback targets are deterministic stable-ID names under:

```text
recovered/spawnpk/fallback/CLIENT_CLASS_XXXXXX
```

The exact stable-ID ordinals computed from the authority's sorted `rs/**` class names agree with the canonical class IDs used by the accepted semantic review.

Total class mappings in the acceptance rewrite:

```text
32 accepted semantic remaps
85 non-semantic source-safety fallbacks
117 total class mappings
```

No UNKNOWN/CANDIDATE class is semantically promoted by the fallback.

## Independent ASM rewrite verification

An independent JDK 21 ASM rewrite was run against the exact authority using the same 117 class mappings. Constant pools were rebuilt rather than copied from the source reader.

Result:

```text
source entries:                       10,970
output entries:                       10,970
output classes:                       10,472
class parse/path errors:                   0
mapped targets missing:                    0
mapped source paths stale:                 0
rs/** class/package collision roots:       0
manifest Main-Class:                 rs/gui/Launcher
manifest Main-Class present:             true
service descriptors:                       2
missing bundled service providers:         0
```

Independent transformed-JAR SHA-256:

```text
b99c2cadc09e3672dbf6fbb83203b0db37ed43631bdabb28fd7d2558a5a9357a
```

That output hash is validation evidence only. The transformed JAR is not committed.

## Scope clarification

The acceptance target is the SpawnPK project namespace, `rs/**`.

The original JAR also contains 85 class/package collision roots outside `rs/**`, primarily in bundled dependency/other namespaces. Those are unchanged by R8A and remain 85 after the rewrite. This is expected: Main's build-authority boundary defaults to `class_prefix = "rs/"`, and R8A must not rename third-party dependency classes merely to make a global archive metric reach zero.

Therefore the precise R8A result is:

> exact-v308 SpawnPK `rs/**` class/package collision roots: **88 -> 85 -> 0**

not "all namespaces in the complete dependency-bearing archive have zero collisions."

## CI

The implementation head `5cb6c3305792eee8747067773f5e3ccdce252a07` passed Recovery CI on both Ubuntu and Windows before this evidence-only report commit.

## Acceptance

R8A satisfies the source-safety portion of #61 without weakening semantic acceptance, member safety, or later clean-rebuild/round-trip gates.

R8B remains separate: add hash-pinned Procyon support, then continue the exact-v308 R4C -> R5A/B/D/E run.
