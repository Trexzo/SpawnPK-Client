# Chat 2 — exact-v308 OsrsMapDependencyScannerTest R253

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/cache/osrs/util/OsrsMapDependencyScannerTest`
- stable ID: `CLIENT_CLASS_000106`
- proposed name: `OsrsMapDependencyScannerTest`
- confidence: **0.999**
- review: `SEMREVIEW_C070282670DDF0B00312`
- unresolved: **0**
- field/method proposals: **0**

## Exact identity

The class name survives unobfuscated in the exact v308 JAR. The full canonical
`seed_lineage()` ordering places it at `CLIENT_CLASS_000106`.

Its executable behavior independently confirms the preserved name: the public static
`main(String[])` is a deterministic regression harness for the reviewed
`OsrsMapDependencyScanner`.

Surviving fixtures/assertions cover:

- extended object-ID smart decoding;
- truncated landscape spawns;
- trailing landscape bytes;
- out-of-range planes;
- packed frame enumeration;
- temporary `osrs-map-audit-test-` filesystem fixtures.

One callback assertion expects the exact decoded tuple `32769:0:10:2`, which was
already useful evidence for the reviewed scanner callback family.

## Naming boundary

R253 records a surviving exact class identifier. It does not infer additional production
authority from the fact that the test harness is shipped inside the client JAR.

## Acceptance boundary

R253 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.
