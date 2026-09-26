# Chat 2 — exact-v308 keyframe / bone animation semantics R44

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R44 is a separate non-canonical class-only semantic review batch. It extends R43's
`Skeleton` / `AnimationFrame` work into the exact-v308 keyframed skeletal-animation
subsystem.

## Deterministic review result

- candidate classes: **5**
- resolved proposals: **5**
- unresolved: **0**
- review ID: `SEMREVIEW_44CE9C7A13841A702A16`
- field/method proposals: **0**

## Stable-ID verification

The IDs were derived from Core's exact `seed_lineage()` ordering over the complete
`rs/` baseline, not inferred from neighboring proposal numbers:

- `rs/u/a` -> `CLIENT_CLASS_001006`
- `rs/u/b` -> `CLIENT_CLASS_001007`
- `rs/u/d` -> `CLIENT_CLASS_001009`
- `rs/u/g` -> `CLIENT_CLASS_001012`
- `rs/u/j` -> `CLIENT_CLASS_001015`

## `rs/u/b` -> `KeyframeAnimation`

This identity has surviving literal evidence: the loader emits
`Not a keyframe file!` when the expected format marker is absent.

The class then constructs/binds an R43 `Skeleton`, decodes curve channels and applies
sampled rotation, translation and scale matrices to bones. Model's skeletal-animation
path consumes the same object.

## `rs/u/a` -> `Keyframe`

One record stores:

- integer sample time/position;
- sample value;
- four tangent/control floats;
- pointer to the following record.

`AnimationCurve` decodes these records into an ordered array, links each entry to its
successor and uses them as the neighboring control samples for interpolation.

## `rs/u/g` -> `AnimationCurve`

The class owns the Keyframe array and pre/post interpolation modes. It locates the active
keyframe interval by time, evaluates between neighboring samples, handles extrapolation,
and contains the cubic coefficient-solving/interpolation machinery.

`KeyframeAnimation` stores these curve objects as transform/property channels and samples
them to drive skeletal transforms.

## `rs/u/d` -> `Bone`

Each record stores a parent index and later a resolved parent Bone reference. It owns
per-variant bind/local matrices, lazily composed parent/global transforms and derived
translation/rotation/scale vectors.

`KeyframeAnimation` builds a transform matrix from sampled channels and writes it to one
of these records.

## `rs/u/j` -> `BoneHierarchy`

This object owns the Bone array. After loading, it resolves each Bone's parent pointer from
its stored parent index.

It is optionally owned by R43 `Skeleton` and applies one `KeyframeAnimation` across
its Bone array, including the masked/blended dispatch path.

## Deliberately withheld adjacent classes

R44 does not force semantic names onto `rs/u/c`, `rs/u/e`, `rs/u/h`, or `rs/u/i`.
Their roles are clearly animation channel/interpolation helpers or enums, but the exact
semantic nouns for each are less uniquely anchored than the five proposals above.

## Naming boundary

All five names are semantic recovery names, not claims of verbatim original SpawnPK
developer identifiers.

## Acceptance boundary

Chat 2 does not promote R44. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_44CE9C7A13841A702A16`.
