# Chat 2 — exact-v308 OsrsMapDependencyScanner R199

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R199 closes one exact-source-name gap left by the earlier R100/R101 scanner-support reviews.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_34B97388290790B025D2`
- field/method proposals: **0**

## Stable ID

`rs/cache/osrs/util/OsrsMapDependencyScanner`
-> `CLIENT_CLASS_000102`
-> `OsrsMapDependencyScanner`

R100/R101 already recover the scanner-specific override loaders and three nested support
types. The readable outer scanner name itself was not previously proposed.

## Exact surviving identity

The v308 class path preserves:

`OsrsMapDependencyScanner`

verbatim.

Its command-line contract also preserves:

`Usage: OsrsMapDependencyScanner [cache-directory] [maps.yaml] [report.txt]`

and:

`Exit: 0 clean, 1 dependency findings, 2 incomplete scan/setup error.`

This is therefore not a reconstructed English role.

## Exact scan responsibility

The scanner preserves exact diagnostics and report vocabulary for:

- `OSRS map dependency scan:`;
- missing object definitions;
- missing sequence definitions;
- missing frame/keyframe files;
- invalid legacy frame data;
- skeletal-keyframe mismatch;
- truncated/invalid landscape data;
- spawned object dependencies;
- recursive `dependencyObject=` findings.

It owns the findings map consumed by the R101 `DependencyFinding` record and recursively
walks dependent object/animation assets.

## Exact inputs

The scanner reads or resolves:

- cache / `main_file_cache`;
- `configs/maps.yaml`;
- `osrs_config/loc.dat`;
- `osrs_config/loc.idx`;
- client object/animation override YAML/config sources.

It explicitly documents that the scan:

`Uses client object/animation overrides and configs/*.yaml, not serialized production configs.`

## Exact report output

The default output is:

`dumps/osrs-map-dependencies.txt`

The scanner prevents the report from overwriting the cache or maps YAML, emits grouped
finding context, and preserves the clean result:

`No missing dependencies found.`

## Naming boundary

`OsrsMapDependencyScanner` is **0.999** because the exact binary name survives and its
complete CLI/cache/map/report responsibility agrees with that name.

No nested-class renaming is added here; R100/R101 already cover the scanner-specific
override and support types.

## Acceptance boundary

Chat 2 does not promote R199. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_34B97388290790B025D2`.
