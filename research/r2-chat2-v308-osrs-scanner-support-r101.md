# Chat 2 — exact-v308 OSRS scanner support records R101

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R101 is a separate non-canonical class-only review for the three nested support types owned
by the readable exact-v308 `OsrsMapDependencyScanner`.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_CDE160288E6CD662B526`
- field/method proposals: **0**
- confidence: **0.997** each

## Stable IDs

- `rs/cache/osrs/util/OsrsMapDependencyScanner$a`
  -> `CLIENT_CLASS_000103`
  -> `DependencyFinding`
- `rs/cache/osrs/util/OsrsMapDependencyScanner$b`
  -> `CLIENT_CLASS_000104`
  -> `LandscapeObjectConsumer`
- `rs/cache/osrs/util/OsrsMapDependencyScanner$c`
  -> `CLIENT_CLASS_000105`
  -> `CacheStoreReader`

## DependencyFinding

The first nested type is an immutable three-field record:

- integer dependency object ID;
- dependency/asset description String;
- finding-reason String.

The scanner creates these records while recursively auditing one root spawned object and
its dependent objects/animations. Exact reasons include:

- `MISSING_DEFINITION`;
- `MISSING_SEQUENCE`;
- frame/keyframe missing or invalid cases;
- decode failures.

They are stored as:

`Map<Integer, List<...>>`

keyed by the root spawned object.

The report prints them under the exact heading:

`Findings (one example spawn per region/root object/dependency):`

and combines the root object with the nested record's dependency-object ID, asset text and
finding reason.

That fixes the record's role as one dependency finding rather than a generic tuple.

## LandscapeObjectConsumer

The second nested type is a one-method interface:

`void accept(int, int, int, int)`

The exact landscape parser decodes:

1. delta-compressed object ID;
2. delta-compressed packed local location;
3. object type from the placement byte;
4. rotation from the same placement byte.

It then invokes the interface with exactly those four values.

The bundled exact-v308 regression test independently verifies this callback contract using
a lambda and the decoded tuple:

`32769:0:10:2`

The main scanner uses the callback while walking packed OSRS landscape data to count spawns
and seed recursive object-dependency checks.

## CacheStoreReader

The third nested helper implements `AutoCloseable`.

It owns:

- a configured cache directory;
- a configured file prefix;
- one shared read-only `<prefix>.dat` RandomAccessFile;
- lazily opened read-only `<prefix>.idxN` RandomAccessFiles.

Its read operation receives:

- cache index;
- numeric archive/file ID;
- whether the returned payload should be GZIP-decoded.

It constructs the existing low-level cache-store reader from the shared data file and
selected index file, reads the requested ID, and optionally returns decompressed bytes.

The scanner owns exactly two instances:

- `main_file_cache`;
- `main_file_osrs`.

Those readers supply the scanner's config, model, animation/frame and landscape bytes.

`close()` closes all lazily opened index files and then the shared data file.

## Relationship to R70 / R100

R70 recovers the runtime OSRS pack/import path:

- `OsrsCacheIndex`;
- `OsrsAssetPacker`.

R100 recovers the scanner-specific YAML override adapters:

- `OsrsSequenceOverrideLoader`;
- `OsrsObjectOverrideLoader`.

R101 covers the remaining nested support contracts of the readable diagnostic scanner
itself. It deliberately does not name `rs/cache/osrs/c`, whose shared runtime mode/array
context is real but whose best class noun is still not proven strongly enough.

## Naming boundary

All three R101 names are descriptive exact-behavior recovery names. No surviving original
nested source nouns were found, so confidence remains 0.997 rather than 0.999.

## Acceptance boundary

Chat 2 does not promote R101. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_CDE160288E6CD662B526`.
