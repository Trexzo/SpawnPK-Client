# Chat 2 — exact-v308 SkyboxPlugin source identity R312

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/k/p` -> `CLIENT_CLASS_000347` -> `SkyboxPlugin`
- proposal: `SEMPROP_8379EBD22A88342BD556`
- review: `SEMREVIEW_19086D64465E7B7F3109`
- unresolved: **0**
- member proposals: **0**

## Why R312 revisits the R91 boundary

R91 correctly recovered `rs/k/o` as `Skybox` but deliberately left adjacent `rs/k/p` unnamed because the SpawnPK class is a thin/pruned wrapper and is not byte-identical to the full public plugin.

R312 does not weaken that byte-identity warning. It adds a stronger source-identity fingerprint that was not used as naming authority in R91.

## Exact-v308 fingerprint

The constructor of `rs/k/p` does exactly this semantic sequence:

1. resolves the bundled resource `skybox.txt` through the class loader;
2. constructs reviewed `rs/k/o` / `Skybox` from that stream;
3. passes the same literal `skybox.txt` as the source name.

Its private three-integer helper is equally distinctive:

- subtract client base X / 8 from the first chunk coordinate;
- subtract client base Y / 8 from the second;
- select the requested plane from the instance-template chunk array;
- return `-1` when either coordinate is outside the selected array;
- otherwise return that exact template-chunk entry.

## Upstream source provenance

RuneLite's public `SkyboxPlugin` contains the same paired fingerprint:

- startup loads `skybox.txt` and constructs `Skybox(in, "skybox.txt")`;
- `mapChunk(int cx, int cy, int plane)` performs the same base-coordinate division, plane selection, bounds check and `-1` fallback.

That paired fingerprint is substantially stronger than merely observing a skybox-related field.

SpawnPK has pruned/adapted the full plugin body, so R312 does **not** claim whole-source byte identity. The semantic proposal recovers the upstream class noun from source provenance.

## Exact runtime wiring

Exact v308 GPU initialization constructs `rs/k/p` into `Client.b`.

Both reviewed client render paths call `Client.b.a()` only after the GPU renderer is active. The remaining hook checks skybox/runtime state and reads local-player coordinate state, matching the surviving portion of the skybox render/update responsibility.

## Boundary

R312 is non-canonical semantic research only. It does not promote `SkyboxPlugin` into canonical lineage and does not rename fields or methods.

The intentionally ambiguous holdouts recorded in the after-R275 frontier note remain withheld.
