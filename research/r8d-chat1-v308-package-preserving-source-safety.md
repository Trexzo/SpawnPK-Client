# R8D Main correction — package-preserving exact-v308 source safety

Date: 2026-09-22

R8D corrects the first R8A fallback shape after exact-v308 runtime-resource review and
reconciles that correction with the already-merged R8B/R8C pipeline.

Generated client JARs, transformed JARs, recovered source and private exact-client
artifacts remain uncommitted.

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

## Why the original global fallback package is superseded

The first R8A implementation moved residual class/package collision roots into:

```text
recovered/spawnpk/fallback/CLIENT_CLASS_*
```

The existing class-remap risk gate correctly reported 49 package-resource risks.

Exact-v308 review found a concrete runtime-sensitive case:

```text
rs/gui/b
  -> Class.getResource("RuneLite.colorschemes")
```

`Class.getResource(String)` with a relative resource name resolves relative to the
class package. Moving this class from `rs.gui` into a global fallback package therefore
changes resource lookup semantics.

Main/Core does not waive that risk. The global fallback-package design is superseded.

## R8D strategy

R8D uses a deterministic package-preserving simple-class rename:

```text
rs/gui/b
  ->
rs/gui/Recovered_CLIENT_CLASS_...
```

Properties:

- the stable logical class ID still determines the fallback name;
- the original package remains unchanged;
- ACCEPTED semantic remaps still take precedence;
- UNKNOWN/CANDIDATE semantic state is not promoted or mutated;
- provenance is explicitly source-safety, never semantic recovery;
- relative package-resource lookup semantics remain unchanged;
- R8C clean-rebuild ownership remains naturally covered by `rs/**`.

The fallback configuration surface is now a simple-name prefix:

```text
fallback_name_prefix = "Recovered_"
```

not a fallback package.

## Resource-risk model correction

Package resources are only a package-move risk when:

```text
source package != target package
```

A package-preserving class rename no longer produces a false package-resource blocker.

This does not weaken the resource gate for actual package moves.

## Exact-v308 namespace result

Fresh canonical regeneration plus the committed 39-proposal semantic acceptance produced:

```text
source_safety_fallbacks: 85
accepted semantic classes: 32
total class remaps: 117
accepted fields: 3
accepted methods: 4
```

Risk report after the package-preserving correction:

```text
literal_class_name_hit_count: 0
package_resource_hit_count: 0
service_descriptor_count: 2
manifest_requires_review: true
```

## Verified ASM rewrite

Private exact-v308 validation produced:

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

Independent transformed-JAR verification:

```text
verification_pass: true
mapped_class_checks: 117
issues: 0
service_descriptors: 2
missing_internal_service_providers: 0
manifest_main_class: rs/gui/Launcher
manifest_main_class_present: true
```

## R8A acceptance target under the corrected strategy

Collision counting is scoped to SpawnPK `rs/**` classes, matching issue #61.

Before source-safety fallback, after accepted semantic remaps:

```text
remaining rs/** class/package collision roots: 85
```

After the R8D package-preserving rewrite:

```text
remaining rs/** class/package collision roots: 0
remaining rs/** class/package collision pairs: 0
```

So the original R8A functional target remains satisfied while preserving package-relative
resource semantics.

## R8B/R8C compatibility

R8B Procyon support is unaffected.

R8C project ownership simplifies under R8D:

```text
project_source_prefixes:
- rs/
- recovered/spawnpk/client/   # when accepted semantic moves use it
```

Fallback-renamed SpawnPK classes remain under `rs/**`, so they stay project-owned and
cannot enter the dependency capsule. No separate fallback package ownership prefix is
required.

## Validation

Affected-surface local regression run:

```text
26 tests
26 passed
Python compileall PASS
```

The repository pull request must additionally pass the existing Linux + Windows Recovery CI
before integration.

No semantic, member-safety, decompiler-hash, clean-rebuild or round-trip proof boundary is
weakened by this correction.
