# Chat 2 — exact-v308 ConfigStore R388

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/e/c` -> `CLIENT_CLASS_000147` -> `ConfigStore`
- proposal: `SEMPROP_831188DDACB318AA26B5`
- review: `SEMREVIEW_9A628AC984061AA0021E`

## Relationship to R16

R16 recovered the surrounding configuration framework and explicitly described
`ConfigManager` as owning a `ConfigStore`, but `rs/e/c` itself was never proposed.

R388 closes that missing class identity.

## Exact storage lifecycle

The constructor accepts one backing File and loads it as UTF-8
`java.util.Properties`. Missing files are tolerated; other load failures become runtime
errors.

Loaded properties populate a concurrent live String->String map.

Mutations update that live map and record only changed keys in a synchronized dirty-delta
map. Removal records the key with a null dirty value. A drain method swaps out the current
dirty map and starts a fresh one.

## Exact persistence behavior

The write path:

1. reloads/merges the backing properties;
2. applies the pending delta;
3. writes UTF-8 properties to a temporary sibling file;
4. holds a FileChannel lock during the write;
5. flushes and calls `force(true)`;
6. moves the temporary file over the target using
   `ATOMIC_MOVE + REPLACE_EXISTING`;
7. falls back to ordinary replacement when atomic moves are unsupported.

This is the durable file-backed storage layer beneath R16 `ConfigManager`, not a config
proxy or descriptor.

R388 remains non-canonical semantic research only.
