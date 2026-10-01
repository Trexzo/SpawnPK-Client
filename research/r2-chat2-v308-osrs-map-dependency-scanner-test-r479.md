# Chat 2 — exact-v308 OsrsMapDependencyScannerTest R479

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/cache/osrs/util/OsrsMapDependencyScannerTest`
- `CLIENT_CLASS_000106`
- exact surviving name: `OsrsMapDependencyScannerTest`
- proposal: `SEMPROP_9C5825CB697C8B46E0D3`
- review: `SEMREVIEW_C070282670DDF0B00312`

## Exact identity

The public class name survives in both the exact class file and recovered source path.

Its standalone regression harness exercises the R199 scanner's exact dependency-decoding
surface, including:

- extended object-ID smart decoding;
- truncated and trailing landscape data;
- out-of-range plane handling;
- packed classic-frame enumeration;
- OSRS-only filtering/counts;
- missing definition/model/sequence/frame/keyframe cases;
- morph dependency provenance;
- finding deduplication.

The exact terminal success literal is:

`OSRS map dependency regression tests passed`

## Stable-ID join

The package sequence is fixed by existing reviews:

- scanner outer: `CLIENT_CLASS_000102`
- scanner nested helpers: `000103..000105`
- **scanner test: `000106`**
- scanner-specific top-level loaders: `000107..000108`

R479 remains non-canonical semantic research only.
