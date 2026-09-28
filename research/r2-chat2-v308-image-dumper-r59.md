# Chat 2 — exact-v308 image dumper semantics R59

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R59 is a separate non-canonical class-only semantic review batch for an exact-v308
development/test image-export helper.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_FB14649050E4209EBF65`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/g` -> `CLIENT_CLASS_000176`

## `rs/g` -> `ImageDumper`

The class has a hard-coded output root:

`./tests/`

and two overloads taking:

- output name;
- width;
- height;
- either `byte[]` pixels or `int[]` pixels.

Both methods create a `BufferedImage`, copy each buffer element into the corresponding
pixel with `setRGB`, create `./tests/<name>.png`, and write the result using
`ImageIO.write(..., "png", file)`.

The surviving diagnostic is:

`Dumped image to: <absolute path>`

That behavior fixes the class as a PNG image-dump/test-export utility. The conservative
semantic name is `ImageDumper`.

## Naming boundary

This is a semantic recovery name, not a claim of a verbatim original SpawnPK identifier.

## Acceptance boundary

Chat 2 does not promote R59. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_FB14649050E4209EBF65`.
