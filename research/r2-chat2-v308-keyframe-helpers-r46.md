# Chat 2 — exact-v308 keyframe helper semantics R46

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R46 completes the clearly recoverable helper portion of the `rs/u/*` keyframe-animation
lane. Exact v308 bytecode remains the authority. A public deobfuscated client containing the
same surviving `Not a keyframe file!` format is used only as corroborating structural
evidence.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_3DFADAD7721E385433E6`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering gives:

- `rs/u/c` -> `CLIENT_CLASS_001008`
- `rs/u/e` -> `CLIENT_CLASS_001010`
- `rs/u/f` -> `CLIENT_CLASS_001011`
- `rs/u/h` -> `CLIENT_CLASS_001013`

## `rs/u/c` -> `AnimationTransformType`

R44 `KeyframeAnimation` decodes one value of this type per animation curve record. The
selected instance determines:

- the number of component channels allocated for that transform family;
- whether the curve belongs to the skeletal Bone array or the ordinary Skeleton transform
  array;
- whether the animation modifies transparency.

The six instances have dimensions **0, 9, 3, 6, 1, 3**. The nine-channel family is the
bone rotation/translation/scale transform set; the one-channel family is the alpha /
transparency transform.

The corroborating source has the exact same six-instance layout under `AnimTransform`
with NULL, VERTEX, COLOUR and TRANSPARENCY roles. The semantic name
`AnimationTransformType` keeps the role explicit without claiming that community label as
original authority.

## `rs/u/e` -> `AnimationChannel`

This 17-instance encoded value set supplies the component index where one
`AnimationCurve` is stored inside its selected transform family.

Exact v308 bone application consumes component indices:

- 0-2 as rotation X/Y/Z;
- 3-5 as translation X/Y/Z;
- 6-8 as scale X/Y/Z.

The one-channel transparency transform uses component 0. Additional instances select
non-bone property/color channels.

The corroborating source exposes the exact same 17-entry table as
`AnimationChannel`, including named rotation, translation, scale and transparency entries.

## `rs/u/f` -> `InterpolationConstants`

This class has no instance state and cannot be instantiated normally. It defines only:

- `Math.ulp(1.0F)`;
- twice that value.

R44 `AnimationCurve` consumes both throughout cubic control-point clamping and its
polynomial/root interpolation solver. `InterpolationConstants` is therefore narrower and
more accurate than the broader community label `AnimationConstants`.

## `rs/u/h` -> `InterpolationPolynomial`

This object contains:

- a float coefficient vector;
- one integer polynomial degree/count.

Its static evaluator is Horner's method. Another helper derives the coefficient vector for
the polynomial derivative.

`AnimationCurve` constructs this object specifically while recursively finding roots for
its timing-interpolation polynomial and passes it into the bracketing/root solver.

The corroborating client calls the same structure `InterpolationChain`; R46 uses
`InterpolationPolynomial` because that directly states the proven mathematical role.

## Lane boundary

With R43-R46, every `rs/u/a` through `rs/u/j` class now has a high-confidence semantic
role except no extra aliases are forced beyond the exact evidence. R46 does not turn any of
these names into canonical mappings.

## Acceptance boundary

Chat 2 does not promote R46. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_3DFADAD7721E385433E6`.
