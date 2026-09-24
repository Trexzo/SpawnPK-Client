# Chat 2 — exact-v308 progress component R166

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R166 is a separate non-canonical class-only review for a reusable horizontal progress
component.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_DD66FE413150F4F4C6A4`
- field/method proposals: **0**

## Stable ID

`rs/ui/components/y` -> `CLIENT_CLASS_001093` -> `ProgressBar`

## Exact component behavior

The class extends `JPanel` and owns exactly two integer progress values.

Its maximum setter clamps the value to at least **1**. Its current-value setter stores the
new current value and repaints.

The percentage accessor computes:

`current * 100 / maximum`

The custom renderer computes:

`filledWidth = current * componentWidth / maximum`

and paints:

1. the unfilled region using a darker derivative of the foreground color;
2. the filled region from the left edge using the foreground color.

The component is configured as a thin horizontal strip:

- preferred height: **4**;
- minimum height: **4**;
- maximum height: **4**;
- maximum width: `Integer.MAX_VALUE`.

This fixes the class as a generic progress bar rather than a feature-specific panel.

## Exact live consumer

Exact-v308 has one project consumer:

`rs/s/t/d`

R14 already recovers that class as `TradingPostListingPanel`.

The listing panel:

- creates one `rs/ui/components/y`;
- places it at `BorderLayout.SOUTH`;
- sets its foreground color from listing state;
- writes maximum/current listing values;
- reads the component percentage for listing tooltip/status text.

This proves live use while preserving the component's feature-agnostic implementation
boundary.

## Naming boundary

`ProgressBar` is descriptive at **0.999**.

The original simple identifier is stripped. The name follows exact state, geometry and paint
behavior and deliberately does not embed the current Trading Post consumer into a reusable
component identity.

R166 remains class-only.

## Acceptance boundary

Chat 2 does not promote R166. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_DD66FE413150F4F4C6A4`.
