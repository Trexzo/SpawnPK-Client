# Chat 2 — exact-v308 screen fade overlay / ScriptPacket 26 R132

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R132 is a separate non-canonical class-only review for a full-screen fade transition
overlay and its exact ScriptPacket controller.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_062C81B911F3212CB010`
- field/method proposals: **0**
- confidence: **0.998** each

## Stable IDs

- `rs/l/e/a/k` -> `CLIENT_CLASS_000409` -> `ScreenFadeOverlay`
- `rs/l/e/a/l` -> `CLIENT_CLASS_000410`
  -> `ScreenFadeOverlayPacketHandler`

## ScreenFadeOverlay

`rs/l/e/a/k` extends the client overlay base and is owned by the central
`rs/l/e/f` overlay framework as its static `h` overlay.

Its state is deliberately small:

- one integer duration;
- one integer direction/mode;
- one start timestamp.

When active, it renders one full-screen rectangle using:

- Client width;
- Client height;
- black/color value **0**;
- a computed alpha.

The duration is converted to milliseconds.

The render path computes an alpha ramp from elapsed time:

- positive mode increases alpha toward **255**;
- negative mode computes **255 - ramp**, producing the inverse transition;
- values are clamped to **0..255**;
- reaching the end resets the overlay state/timestamp.

That exact behavior is a screen fade rather than a generic content overlay.

## ScriptPacket 26

R115 registers ScriptPacket **26** from `rs/l/e/a/k.p`.

Exact v308 initializes that field with:

`new rs/l/e/a/l()`

The complete handler reads two integers:

1. fade mode;
2. fade duration.

Mode value **2** is normalized to **-1**; other values are passed through.

It calls only:

`rs/l/e/a/k.a(mode, duration)`

which stores the two packet values and resets the start timestamp.

No unrelated widget, gameplay state or other overlay is touched.

## Naming boundary

`ScreenFadeOverlay` and `ScreenFadeOverlayPacketHandler` are descriptive readable names.
They do not claim that the original source identifiers survived.

Confidence is **0.998** because the visible full-screen black alpha-ramp behavior and the
packet contract are exact, while the original class noun itself is stripped.

## Acceptance boundary

Chat 2 does not promote R132. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_062C81B911F3212CB010`.
