# R8A Main validation — exact-v308 source-safe namespace

Date: 2026-09-22

This records Main/Core validation of the R8A package-preserving source-safety namespace
against the exact v308 authority. Generated lineages, transformed JARs and client binaries
remain private/uncommitted.

## Exact authority

- client SHA-256: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`
- indexed entries: 10,970
- parsed classes: 10,472
- `rs/**` classes: 1,129
- parse errors: 0
- canonical class identities: 1,129
- canonical member identities: 13,811
- semantic review: `SEMREVIEW_DD69CD752A6E46181BAC`
- accepted semantic seed: 32 classes + 3 fields + 4 methods

## Why the first fallback shape was rejected

The first R8A branch revision moved collision-root classes into a global fallback package.
The existing remap risk gate correctly blocked that shape with 49 package-resource risks.

Direct exact-v308 inspection then found a concrete runtime-sensitive case:

- `rs/gui/b` calls `Class.getResource("RuneLite.colorschemes")`.

Moving that class out of package `rs.gui` would change Java-relative resource resolution.
Main therefore rejected the global-package fallback rather than bypassing the risk gate.

R8A was revised to use deterministic package-preserving class renames:

```text
rs/gui/b
  ->
rs/gui/Recovered_CLIENT_CLASS_...
```

The simple fallback name derives from the stable logical class ID. The source package is
preserved, so relative package-resource lookup semantics remain unchanged. This is
source-safety provenance only; it does not promote UNKNOWN/CANDIDATE semantic state.

The risk scanner was correspondingly tightened: package-resource risk is reported only
when a class remap actually changes package.

## Exact-v308 namespace result

Fresh canonical regeneration plus the committed 39-proposal semantic acceptance produced:

```text
source_safety_fallbacks: 85
accepted semantic classes: 32
total class remaps: 117
accepted fields: 3
accepted methods: 4
```

Class remap risk report:

```text
literal_class_name_hit_count: 0
package_resource_hit_count: 0
service_descriptor_count: 2
manifest_requires_review: true
```

The service descriptors and manifest remain under the existing independent rewrite/
verification model.

## Verified ASM rewrite

R8A class rewrite result:

```text
source SHA-256:
854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6

derived class-readable JAR SHA-256:
a9f4d1c656bf4c7ae96e1e15b1f56ca14c0cb3fe42882933e4c15725b226a37b

mapped classes:
117

output entries:
10,970

class parse errors:
0
```

Independent verification:

```text
verification_pass: true
mapped_class_checks: 117
issues: 0
service_descriptors: 2
missing_internal_service_providers: 0
manifest_main_class: rs/gui/Launcher
manifest_main_class_present: true
```

## R8A acceptance target

Collision counting is intentionally scoped to SpawnPK `rs/**` classes, matching #61.

Before R8A (after the accepted semantic remaps):

```text
remaining rs/** class/package collision roots: 85
```

After the package-preserving R8A rewrite:

```text
remaining rs/** class/package collision roots: 0
remaining rs/** class/package collision pairs: 0
```

Therefore the R8A acceptance target from #61 is satisfied without weakening semantic,
member-safety, resource-risk, ASM verification or source authority boundaries.

R8B / Procyon support and the subsequent R4C -> R5 acceptance rerun remain separate work.
