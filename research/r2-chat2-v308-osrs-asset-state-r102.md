# Chat 2 — exact-v308 OSRS asset state R102

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R102 is a separate non-canonical class-only review for the last exact-v308 class in the
`rs/cache/osrs/*` runtime package that was not already covered by R70.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_BFB4BC3B81C92AA0DCA1`
- field/method proposals: **0**
- confidence: **0.996**

## Stable ID

- `rs/cache/osrs/c` -> `CLIENT_CLASS_000101` -> `OsrsAssetState`

## Exact static-state contract

The class has no domain behavior beyond static state access.

It owns exactly:

- one boolean mode flag;
- one alternate `rs/v[]` asset/model-header array;
- one alternate `rs/k[][]` animation/frame matrix.

Every method is a direct getter or setter for one of those three values.

## Model-side use

The model subsystem maintains two separate model-header/cache arrays.

During initialization it allocates:

- the ordinary array;
- a separate OSRS array written through this class.

Model lookup selects the OSRS array when the class mode flag is active.

Several exact call sites temporarily set the flag according to the definition/model being
resolved and restore it afterward, which prevents OSRS asset lookup state from leaking into
ordinary model loading.

## Animation-side use

The animation/frame subsystem likewise maintains:

- its ordinary frame matrix;
- a separate OSRS frame matrix owned through this class.

The exact animation code selects that alternate matrix when OSRS mode is active and contains
surviving OSRS-specific paths and diagnostics including:

- `old_osrs_anims`;
- `Loading OSRS:`;
- `[Animations] Could not find OSRS animation file`.

The skeleton/base constructor also reads the same mode flag while decoding animation data.

## Request-side use

R24 `OnDemandFetcher` reads the active mode flag when creating cache requests and records
the OSRS/ordinary selection on the request object.

That independently confirms that the boolean is not merely a rendering toggle: it is the
shared asset/cache selection state consumed by model, animation and cache-fetch paths.

## Relationship to R70 / R100 / R101

- R70 names the OSRS cache index enum and loose-asset packer.
- R100 names the scanner-only sequence/object override loaders.
- R101 names the scanner's nested finding/callback/cache-reader support types.
- R102 covers the shared runtime OSRS asset-selection state used outside the standalone
  scanner.

## Naming boundary

No surviving public or historical source noun was found for this class.

`OsrsAssetState` is therefore explicitly descriptive rather than claimed as an original
developer identifier. Confidence is **0.996**, lower than source-name-backed reviews.

The name is intentionally narrower than `OsrsRuntimeContext`: the proven state is asset
selection and alternate model/animation caches, not arbitrary runtime state.

## Acceptance boundary

Chat 2 does not promote R102. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_BFB4BC3B81C92AA0DCA1`.
