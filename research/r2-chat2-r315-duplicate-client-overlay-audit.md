# Chat 2 — R315 duplicate ClientOverlay audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R315 retains **no semantic proposal**.

The attempted `rs/l/e/f -> InterfaceFeatureController` proposal was rejected by the
repository-wide uniqueness gate because R111 already owns the exact class:

- `rs/l/e/f`
- `CLIENT_CLASS_000426`
- `ClientOverlay`
- R111 proposal: `SEMPROP_C34CE74D45B1BEDABA72`
- R111 review: `SEMREVIEW_2520A829D44C8379CCD5`

The failed attempted R315 review was removed completely.

## Why the attempted name was redundant

The new R302/R314 evidence does not establish a different class. It strengthens R111's
existing `ClientOverlay` interpretation.

R111 already proved that the abstract class:

- owns the live overlay registry;
- participates in LOW/HIGH client render passes;
- exposes lifecycle/reset hooks;
- owns interface/callback handlers through a base-owned int-keyed map.

R302 and R314 add a stronger rendering join:

- R302 fixes the central widget traversal class as `InterfaceRenderer`;
- R314 fixes `rs/l/e/i` as `InterfaceWidgetRenderCallback`;
- `InterfaceRenderer` iterates active `rs/l/e/f` overlays/controllers;
- each `rs/l/e/f` instance can register widget-id keyed callbacks;
- the renderer looks up callbacks using the concrete `RSInterface.aw` id and dispatches
  them with the concrete widget plus resolved x/y coordinates.

That callback registry is therefore an additional responsibility of the already-reviewed
`ClientOverlay` base, not evidence for a second semantic identity.

## CI evidence

Attempted R315 Recovery CI:

- run: `36373884412`
- Ubuntu: failed in unit tests
- Windows: failed in unit tests
- exact failure:
  `duplicate class owner rs/l/e/f: R111 and R315`

The deterministic R315 proposal/review IDs themselves were internally consistent; the
failure was specifically the global semantic uniqueness guard doing its job.

Cleanup commit removed the four attempted R315 candidate/review/research/test files.

## Nearby withheld classes

`rs/l/e/l` + `rs/l/e/m` remain intentionally unnamed.

Their queued/sliding text behavior is structurally understood, but no surviving producer or
domain noun has been found that justifies a precise feature name.

`rs/n/c/x` + `rs/n/c/y` also remain intentionally unnamed.

Exact-v308 evidence still fixes them as adjacent construction-interface builders, with
`rs/n/c/x` laying out eight entries containing `Name1..Name8`, `lvl1..lvl8` and
four requirement rows per entry using `construction/sprite 1`, while `rs/n/c/y`
builds the neighboring `construction/sprite 0` panel. The evidence still does not
distinguish a precise historical noun such as furniture selection, build options or
requirements.

## Boundary

R315 is a correction/corroboration note only.

No candidate JSON, semantic-review JSON, acceptance spec or source rewrite is retained.
